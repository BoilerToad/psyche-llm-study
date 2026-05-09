#!/usr/bin/env python3
"""
judge_responses.py
──────────────────
Feed collected model responses to a judge LLM for analysis.

For each question, builds a prompt containing all model responses and asks
the judge to summarize patterns, highlight notable findings, and flag outliers.

Output:
  experiments/<id>/analysis/judge_TIMESTAMP.md   — human-readable report
  experiments/<id>/analysis/judge_TIMESTAMP.db   — queryable SQLite archive

Usage:
    python scripts/judge_responses.py --experiment pilot-2026-05
    python scripts/judge_responses.py --experiment pilot-2026-05 --questions Q01,Q03
    python scripts/judge_responses.py --experiment pilot-2026-05 --judge grok-3
    python scripts/judge_responses.py --experiment pilot-2026-05 --db results/run_2026-05-09.db
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from llm_client import LLMClient


DEFAULT_JUDGE = "mistral-large-3:675b-cloud"

JUDGE_PROMPT_TEMPLATE = """\
You are analyzing responses from multiple LLMs to the following psychology question.

QUESTION ({category}): {prompt}

RESPONSES ({n_models} models):
{responses}

Provide a structured analysis covering:
1. **Summary** — main themes and patterns across responses
2. **Agreements** — where models converge
3. **Disagreements / Outliers** — notable differences or surprising stances
4. **Standout responses** — particularly insightful, nuanced, or poor responses (name the model)
5. **Overall assessment** — quality and depth across the model set
"""


# ── SQLite helpers ────────────────────────────────────────────────────────────

def init_judge_db(db_path):
    """Create the judge DB schema and return (conn, run_id placeholder)."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS judge_runs (
            id          INTEGER PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            source_db   TEXT NOT NULL,
            judge_model TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS judge_analyses (
            id               INTEGER PRIMARY KEY,
            run_id           INTEGER NOT NULL,
            question_id      TEXT NOT NULL,
            category         TEXT,
            question_prompt  TEXT,
            models_included  INTEGER,
            models_skipped   TEXT,
            judge_response   TEXT,
            elapsed_seconds  REAL,
            success          INTEGER NOT NULL,
            created_at       TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES judge_runs(id)
        )
    """)
    conn.commit()
    return conn


def insert_run(conn, experiment_id, source_db, judge_model):
    """Insert a judge_runs row and return its id."""
    cursor = conn.execute(
        "INSERT INTO judge_runs (experiment_id, source_db, judge_model, created_at) "
        "VALUES (?, ?, ?, ?)",
        (experiment_id, str(source_db), judge_model, datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def insert_analysis(conn, run_id, result):
    """Insert one judge_analyses row from a result dict."""
    conn.execute(
        "INSERT INTO judge_analyses "
        "(run_id, question_id, category, question_prompt, models_included, "
        " models_skipped, judge_response, elapsed_seconds, success, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            result["question_id"],
            result["category"],
            result["question_prompt"],
            result["models_included"],
            json.dumps(result["models_skipped"]),
            result["judge_response"],
            result["elapsed_seconds"],
            int(result["success"]),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()


# ── Response loading ──────────────────────────────────────────────────────────

def find_latest_db(results_dir):
    """Return the most recently modified run_*.db in results_dir, or None."""
    db_files = list(results_dir.glob("run_*.db"))
    if not db_files:
        return None
    return max(db_files, key=lambda p: p.stat().st_mtime)


def load_responses(db_path, question_filter=None):
    """Load responses from DB grouped by question ID."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT model_name, prompt, content, success, elapsed_seconds, tags_json
        FROM queries
        ORDER BY tags_json, model_name
    """)
    rows = cursor.fetchall()
    conn.close()

    questions = {}

    for model_name, prompt, content, success, elapsed_s, tags_json in rows:
        tags = json.loads(tags_json) if tags_json else []
        q_id = next((t for t in tags if t.startswith("Q")), None)
        category = tags[1] if len(tags) > 1 else "unknown"

        if q_id is None:
            continue
        if question_filter and q_id not in question_filter:
            continue

        if q_id not in questions:
            questions[q_id] = {"prompt": prompt, "category": category, "responses": []}

        questions[q_id]["responses"].append({
            "model_name": model_name,
            "content": content,
            "success": bool(success),
            "elapsed_s": elapsed_s or 0.0,
        })

    return questions


# ── Judge logic ───────────────────────────────────────────────────────────────

def build_judge_prompt(q_data):
    """Build the judge prompt for one question. Returns (prompt_str, skipped_list)."""
    responses_text = ""
    skipped = []

    for r in q_data["responses"]:
        if not r["success"] or not (r["content"] or "").strip():
            skipped.append(r["model_name"])
            continue
        responses_text += (
            f"\n[{r['model_name']}] ({r['elapsed_s']:.1f}s)\n{r['content'].strip()}\n"
        )

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        category=q_data["category"],
        prompt=q_data["prompt"],
        n_models=len(q_data["responses"]) - len(skipped),
        responses=responses_text.strip(),
    )

    return prompt, skipped


def initialize_judge(model_name):
    """Create and health-check the judge LLMClient. Returns client or exits."""
    try:
        judge = LLMClient(models_file="models.json", model=model_name)
        ok, detail = judge.health_check()
        if not ok:
            print(f"Error: judge model unavailable — {detail}")
            sys.exit(1)
        print(f"Judge available: {detail}\n")
        return judge
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error initializing judge: {e}")
        sys.exit(1)


def analyze_question(judge, q_id, q_data):
    """Run judge on one question. Returns a result dict."""
    n_total = len(q_data["responses"])
    print(f"[{q_id}] Sending {n_total} responses to judge...")

    prompt, skipped = build_judge_prompt(q_data)
    result = judge.chat(prompt, timeout=300)

    if result.success:
        print(f"  ✓ Done ({result.elapsed_s:.1f}s)")
    else:
        print(f"  ✗ Failed: {result.error}")

    return {
        "question_id": q_id,
        "category": q_data["category"],
        "question_prompt": q_data["prompt"],
        "models_included": n_total - len(skipped),
        "models_skipped": skipped,
        "judge_response": result.content if result.success else None,
        "elapsed_seconds": result.elapsed_s,
        "success": result.success,
    }


# ── Output formatting ─────────────────────────────────────────────────────────

def build_header(experiment, judge_model, db_path, questions):
    """Return the markdown header lines for the analysis file."""
    return [
        f"# Judge Analysis — {experiment}",
        f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Judge model:** {judge_model}  ",
        f"**Source:** {db_path}  ",
        f"**Questions analyzed:** {', '.join(sorted(questions.keys()))}",
        "\n---\n",
    ]


def format_question_markdown(result, n_total):
    """Convert a result dict to markdown section lines."""
    lines = [
        f"## {result['question_id']} — {result['category']}",
        f"\n**Question:** {result['question_prompt']}  ",
        f"**Models included:** {result['models_included']}/{n_total}  ",
    ]
    if result["models_skipped"]:
        lines.append(f"**Skipped (failed/empty):** {', '.join(result['models_skipped'])}  ")
    lines.append("")

    if result["success"]:
        lines.append(result["judge_response"])
    else:
        lines.append("_Judge query failed._")

    lines.append("\n---\n")
    return lines


# ── Entry point ───────────────────────────────────────────────────────────────

def main():  # pylint: disable=too-many-locals
    """Parse args, load responses, run judge per question, write outputs."""
    parser = argparse.ArgumentParser(description="Judge LLM responses from an experiment")
    parser.add_argument("--experiment", metavar="ID", required=True,
                        help="Experiment ID under experiments/")
    parser.add_argument("--questions", metavar="Q01,Q02",
                        help="Comma-separated question IDs to analyze (default: all)")
    parser.add_argument("--judge", default=DEFAULT_JUDGE,
                        help=f"Judge model name (default: {DEFAULT_JUDGE})")
    parser.add_argument("--db",
                        help="Specific run DB path (default: latest in experiment results/)")
    args = parser.parse_args()

    exp_dir = Path("experiments") / args.experiment
    if not exp_dir.exists():
        print(f"Error: experiments/{args.experiment}/ not found")
        sys.exit(1)

    source_db = Path(args.db) if args.db else find_latest_db(exp_dir / "results")
    if not source_db:
        print(f"Error: no run_*.db found in experiments/{args.experiment}/results/")
        sys.exit(1)

    print(f"Experiment: {args.experiment}")
    print(f"Database:   {source_db}")
    print(f"Judge:      {args.judge}")

    question_filter = None
    if args.questions:
        question_filter = {q.strip() for q in args.questions.split(",")}
        print(f"Questions:  {', '.join(sorted(question_filter))}")
    else:
        print("Questions:  all")

    questions = load_responses(source_db, question_filter)
    if not questions:
        print("No matching responses found in database.")
        sys.exit(1)

    print(f"\nLoaded {len(questions)} question(s).")

    judge = initialize_judge(args.judge)

    analysis_dir = exp_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    md_path = analysis_dir / f"judge_{timestamp}.md"
    db_path = analysis_dir / f"judge_{timestamp}.db"

    # Set up SQLite
    conn = init_judge_db(db_path)
    run_id = insert_run(conn, args.experiment, source_db, args.judge)

    # Run judge and collect results
    sections = build_header(args.experiment, args.judge, source_db, questions)
    for q_id in sorted(questions.keys()):
        q_data = questions[q_id]
        result = analyze_question(judge, q_id, q_data)
        insert_analysis(conn, run_id, result)
        sections.extend(format_question_markdown(result, len(q_data["responses"])))

    conn.close()

    md_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"\nMarkdown : {md_path}")
    print(f"SQLite   : {db_path}")


if __name__ == "__main__":
    main()
