#!/usr/bin/env python3
"""
summarize_label.py
──────────────────
Extract responses assigned a specific classification label and ask a judge LLM
to summarize what that label actually represents.

Useful after classify_results.py produces an "Other" bucket and you want to
understand what the models in that bucket actually said.

Usage:
    python scripts/summarize_label.py \\
        --experiment newcomb-2026-05 \\
        --question Q02 \\
        --label Other

    # Point at a specific classify DB instead of the latest one:
    python scripts/summarize_label.py \\
        --experiment newcomb-2026-05 \\
        --question Q02 \\
        --label Other \\
        --classify-db experiments/newcomb-2026-05/analysis/classify_Q02_2026-05-09_18-34-20.db
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from llm_client import LLMClient


DEFAULT_JUDGE = "mistral-large-3:675b-cloud"

SUMMARIZE_PROMPT = """\
The following responses were all classified as "{label}" when asked:

CLASSIFICATION QUESTION: {classification_question}

These {n} model responses did not fit neatly into the other categories. \
Please summarize:
1. What themes or patterns appear across these "{label}" responses?
2. Why might they have been hard to classify?
3. If you had to sub-categorize them, what sub-groups would you create?

RESPONSES:
{responses}
"""


# ── DB helpers ────────────────────────────────────────────────────────────────

def find_latest_classify_db(analysis_dir, question_id):
    """Return the most recently modified classify_<question>_*.db, or None."""
    pattern = f"classify_{question_id}_*.db"
    db_files = list(analysis_dir.glob(pattern))
    if not db_files:
        return None
    return max(db_files, key=lambda p: p.stat().st_mtime)


def load_label_rows(db_path, label):
    """Return (classification_question, rows) for rows matching label."""
    import sqlite3  # pylint: disable=import-outside-toplevel
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Pull the classification question from the run metadata
    cursor.execute(
        "SELECT classification_question FROM classify_runs ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    classification_question = row[0] if row else "(unknown)"

    # Pull matching responses
    cursor.execute(
        """
        SELECT c.model_name, c.response_content
        FROM classifications c
        JOIN classify_runs r ON c.run_id = r.id
        WHERE c.classification = ?
        ORDER BY c.model_name
        """,
        (label,),
    )
    rows = cursor.fetchall()
    conn.close()
    return classification_question, rows


# ── Output ────────────────────────────────────────────────────────────────────

def build_prompt(label, classification_question, rows):
    """Format all responses into a single judge prompt."""
    responses_text = ""
    for model_name, content in rows:
        snippet = (content or "").strip()
        responses_text += f"\n[{model_name}]\n{snippet}\n"

    return SUMMARIZE_PROMPT.format(
        label=label,
        classification_question=classification_question,
        n=len(rows),
        responses=responses_text.strip(),
    )


def write_markdown(md_path, meta, rows, judge_response):
    """Write the summary to a markdown file.

    meta keys: experiment, question, label, classify_db, judge_model.
    """
    model_list = ", ".join(r[0] for r in rows)
    experiment = meta["experiment"]
    question = meta["question"]
    label = meta["label"]
    classify_db = meta["classify_db"]
    judge_model = meta["judge_model"]

    lines = [
        f"# Label Summary — {label} / {question} / {experiment}",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Judge:** {judge_model}  ",
        f"**Classify DB:** {classify_db}  ",
        f"**Label filtered:** {label}  ",
        f"**Models ({len(rows)}):** {model_list}",
        "",
        "---",
        "",
        judge_response,
        "",
        "---",
        "",
        "## Raw Responses",
        "",
    ]

    for model_name, content in rows:
        lines += [
            f"### {model_name}",
            "",
            (content or "").strip(),
            "",
        ]

    md_path.write_text("\n".join(lines), encoding="utf-8")


def initialize_judge(model_name):
    """Create and health-check the judge LLMClient. Returns client or exits."""
    try:
        judge = LLMClient(models_file="models.json", model=model_name)
        ok, detail = judge.health_check()
        if not ok:
            print(f"\nError: judge unavailable — {detail}")
            sys.exit(1)
        print(f"\nJudge available: {detail}")
        return judge
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"\nError initializing judge: {exc}")
        sys.exit(1)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():  # pylint: disable=too-many-locals
    """Extract label responses from a classify DB and summarize them with a judge."""
    parser = argparse.ArgumentParser(
        description="Summarize responses classified under a specific label"
    )
    parser.add_argument("--experiment", metavar="ID", required=True,
                        help="Experiment ID under experiments/")
    parser.add_argument("--question", metavar="Q02", required=True,
                        help="Question ID whose classify run to read")
    parser.add_argument("--label", default="Other",
                        help="Classification label to extract (default: Other)")
    parser.add_argument("--classify-db", metavar="PATH",
                        help="Specific classify DB (default: latest classify_<Q>_*.db)")
    parser.add_argument("--judge", default=DEFAULT_JUDGE,
                        help=f"Judge model (default: {DEFAULT_JUDGE})")
    args = parser.parse_args()

    exp_dir = Path("experiments") / args.experiment
    if not exp_dir.exists():
        print(f"Error: experiments/{args.experiment}/ not found")
        sys.exit(1)

    analysis_dir = exp_dir / "analysis"

    if args.classify_db:
        classify_db = Path(args.classify_db)
    else:
        classify_db = find_latest_classify_db(analysis_dir, args.question)

    if not classify_db or not classify_db.exists():
        print(
            f"Error: no classify_{args.question}_*.db found in "
            f"experiments/{args.experiment}/analysis/"
        )
        sys.exit(1)

    print(f"Experiment  : {args.experiment}")
    print(f"Question    : {args.question}")
    print(f"Label       : {args.label}")
    print(f"Classify DB : {classify_db}")
    print(f"Judge       : {args.judge}")

    # Load matching rows
    classification_question, rows = load_label_rows(classify_db, args.label)
    if not rows:
        print(f"\nNo responses found with label '{args.label}'.")
        sys.exit(0)

    print(f"\nFound {len(rows)} '{args.label}' responses:")
    for model_name, _ in rows:
        print(f"  • {model_name}")

    judge = initialize_judge(args.judge)

    # Build prompt and call judge
    prompt = build_prompt(args.label, classification_question, rows)
    print("\nSending to judge...")
    result = judge.chat(prompt, timeout=300)

    if not result.success:
        print(f"Error: judge query failed — {result.error}")
        sys.exit(1)

    print(f"Done ({result.elapsed_s:.1f}s)")

    # Write output
    analysis_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    md_path = analysis_dir / f"summarize_{args.question}_{args.label}_{timestamp}.md"

    meta = {
        "experiment": args.experiment,
        "question": args.question,
        "label": args.label,
        "classify_db": classify_db,
        "judge_model": args.judge,
    }
    write_markdown(md_path, meta, rows, result.content)

    print(f"\nMarkdown: {md_path}")


if __name__ == "__main__":
    main()
