#!/usr/bin/env python3
"""
classify_results.py
───────────────────
Classify model responses from an experiment one-by-one using a judge LLM.
Produces a per-model classification table, a summary tally, and saves
results to SQLite and CSV in experiments/<id>/analysis/.

Usage:
    # Q01 — one-box vs two-box
    python scripts/classify_results.py \\
        --experiment newcomb-2026-05 \\
        --question Q01 \\
        --ask "Did the model choose one-box (take only Box B) or two-box
               (take both boxes)? Reply with A, B, or Other." \\
        --labels "A,B,Other"

    # Q02 — did the model change its answer?
    python scripts/classify_results.py \\
        --experiment newcomb-2026-05 \\
        --question Q02 \\
        --ask "Did the model keep its original answer, change to the opposite,
               or give an unclear response? Reply with Same, Changed, or Other." \\
        --labels "Same,Changed,Other"
"""

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from llm_client import LLMClient


DEFAULT_JUDGE = "mistral-large-3:675b-cloud"

CLASSIFY_PROMPT = """\
Classify the following LLM response. Reply with ONLY the classification label — \
no explanation, no punctuation, just the label.

CLASSIFICATION QUESTION: {ask}

RESPONSE TO CLASSIFY:
{content}
"""


# ── SQLite helpers ────────────────────────────────────────────────────────────

def init_classify_db(db_path):
    """Create classify DB schema and return connection."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classify_runs (
            id                     INTEGER PRIMARY KEY,
            experiment_id          TEXT NOT NULL,
            question_id            TEXT NOT NULL,
            classification_question TEXT NOT NULL,
            valid_labels           TEXT,
            judge_model            TEXT NOT NULL,
            source_db              TEXT NOT NULL,
            created_at             TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classifications (
            id               INTEGER PRIMARY KEY,
            run_id           INTEGER NOT NULL,
            model_name       TEXT NOT NULL,
            response_content TEXT,
            classification   TEXT,
            elapsed_seconds  REAL,
            created_at       TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES classify_runs(id)
        )
    """)
    conn.commit()
    return conn


def insert_run(conn, experiment_id, question_id, ask, labels, judge_model, source_db):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Insert a classify_runs row and return its id."""
    cursor = conn.execute(
        "INSERT INTO classify_runs "
        "(experiment_id, question_id, classification_question, valid_labels, "
        " judge_model, source_db, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (experiment_id, question_id, ask,
         ",".join(labels) if labels else None,
         judge_model, str(source_db), datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def insert_classification(conn, run_id, model_name, content, label, elapsed_s):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Insert one classifications row."""
    conn.execute(
        "INSERT INTO classifications "
        "(run_id, model_name, response_content, classification, elapsed_seconds, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, model_name, content, label, elapsed_s, datetime.now().isoformat()),
    )
    conn.commit()


# ── Response loading ──────────────────────────────────────────────────────────

def find_latest_db(results_dir):
    """Return the most recently modified run_*.db, or None."""
    db_files = list(results_dir.glob("run_*.db"))
    if not db_files:
        return None
    return max(db_files, key=lambda p: p.stat().st_mtime)


def load_responses(db_path, question_id):
    """Load successful responses for a question, one row per model."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT model_name, content, elapsed_seconds
        FROM queries
        WHERE success = 1
          AND tags_json LIKE ?
        ORDER BY model_name
    """, (f'%"{question_id}"%',))
    rows = cursor.fetchall()
    conn.close()
    return [{"model_name": r[0], "content": r[1], "elapsed_s": r[2]} for r in rows]


# ── Classification ────────────────────────────────────────────────────────────

def normalize_label(raw, labels):
    """Return the first word of raw, matched case-insensitively against labels if provided."""
    word = raw.strip().split()[0] if raw.strip() else "Other"
    if not labels:
        return word
    for label in labels:
        if word.lower() == label.lower():
            return label
    return word


def classify_response(judge, content, ask, labels):
    """Send one response to the judge for classification. Returns (label, elapsed_s)."""
    prompt = CLASSIFY_PROMPT.format(ask=ask, content=content)
    result = judge.chat(prompt, timeout=120)
    if not result.success:
        return "Error", result.elapsed_s
    return normalize_label(result.content, labels), result.elapsed_s


# ── Output ────────────────────────────────────────────────────────────────────

def print_results(rows, labels):
    """Print a model/classification table and a summary tally."""
    col_width = max((len(r["model_name"]) for r in rows), default=20)
    header = f"{'Model':<{col_width}} | Classification"
    print("\n" + header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['model_name']:<{col_width}} | {r['classification']}")

    # Tally
    tally = {}
    for r in rows:
        tally[r["classification"]] = tally.get(r["classification"], 0) + 1

    print(f"\nSummary ({len(rows)} models):")
    order = labels if labels else sorted(tally.keys())
    for label in order:
        count = tally.get(label, 0)
        fill = "█" * count
        print(f"  {label:<12} {count:>3}  {fill}")

    unlisted = [k for k in tally if k not in (labels or [])]
    for label in unlisted:
        print(f"  {label:<12} {tally[label]:>3}")


def write_csv(rows, csv_path):
    """Write classification results to CSV."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["model_name", "classification", "elapsed_s"])
        writer.writeheader()
        writer.writerows(rows)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():  # pylint: disable=too-many-locals,too-many-statements
    """Classify model responses from an experiment using a judge LLM."""
    parser = argparse.ArgumentParser(description="Classify experiment responses")
    parser.add_argument("--experiment", metavar="ID", required=True,
                        help="Experiment ID under experiments/")
    parser.add_argument("--question", metavar="Q01", required=True,
                        help="Question ID whose responses to classify")
    parser.add_argument("--ask", required=True,
                        help="Classification question sent to the judge per response")
    parser.add_argument("--labels", metavar="A,B,Other",
                        help="Comma-separated valid labels for normalization (optional)")
    parser.add_argument("--judge", default=DEFAULT_JUDGE,
                        help=f"Judge model name (default: {DEFAULT_JUDGE})")
    parser.add_argument("--db",
                        help="Specific run DB (default: latest in experiment results/)")
    args = parser.parse_args()

    exp_dir = Path("experiments") / args.experiment
    if not exp_dir.exists():
        print(f"Error: experiments/{args.experiment}/ not found")
        sys.exit(1)

    source_db = Path(args.db) if args.db else find_latest_db(exp_dir / "results")
    if not source_db:
        print(f"Error: no run_*.db found in experiments/{args.experiment}/results/")
        sys.exit(1)

    labels = [l.strip() for l in args.labels.split(",")] if args.labels else None

    print(f"Experiment : {args.experiment}")
    print(f"Question   : {args.question}")
    print(f"Judge      : {args.judge}")
    print(f"Labels     : {', '.join(labels) if labels else 'free-form'}")
    print(f"Database   : {source_db}")
    print(f"\nClassification question:\n  {args.ask}\n")

    # Load responses
    responses = load_responses(source_db, args.question)
    if not responses:
        print(f"No successful responses found for {args.question}.")
        sys.exit(1)
    print(f"Loaded {len(responses)} responses.\n")

    # Initialize judge
    judge = LLMClient(models_file="models.json", model=args.judge)
    ok, detail = judge.health_check()
    if not ok:
        print(f"Error: judge unavailable — {detail}")
        sys.exit(1)
    print(f"Judge available: {detail}\n")

    # Set up output files
    analysis_dir = exp_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_db = analysis_dir / f"classify_{args.question}_{timestamp}.db"
    out_csv = analysis_dir / f"classify_{args.question}_{timestamp}.csv"

    conn = init_classify_db(out_db)
    run_id = insert_run(
        conn, args.experiment, args.question, args.ask, labels, args.judge, source_db
    )

    # Classify each response
    rows = []
    for i, resp in enumerate(responses, 1):
        model = resp["model_name"]
        print(f"[{i}/{len(responses)}] {model}...")
        label, elapsed_s = classify_response(judge, resp["content"], args.ask, labels)
        insert_classification(conn, run_id, model, resp["content"], label, elapsed_s)
        rows.append({"model_name": model, "classification": label, "elapsed_s": elapsed_s})
        print(f"  → {label}  ({elapsed_s:.1f}s)")

    conn.close()

    # Output
    print_results(rows, labels)
    write_csv(rows, out_csv)

    print(f"\nSQLite : {out_db}")
    print(f"CSV    : {out_csv}")


if __name__ == "__main__":
    main()
