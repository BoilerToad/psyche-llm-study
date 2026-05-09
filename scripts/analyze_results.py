#!/usr/bin/env python3
"""
analyze_results.py
──────────────────
Analysis script for study results.

Usage:
    python scripts/analyze_results.py --experiment <id>          # latest run in that experiment
    python scripts/analyze_results.py --experiment <id> <db>     # specific run
    python scripts/analyze_results.py <db>                        # specific db by path
    python scripts/analyze_results.py                             # latest in results/
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def analyze_study(db_path: str):  # pylint: disable=too-many-locals,too-many-statements
    """Perform basic analysis on study results."""

    if not Path(db_path).exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    print(f"Analyzing: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Study metadata
    print("="*70)
    print("STUDY METADATA")
    print("="*70)
    cursor.execute("SELECT * FROM experiments")
    for row in cursor.fetchall():
        exp_id, name, desc, created_at, metadata = row
        print(f"Experiment ID: {exp_id}")
        print(f"Name: {name}")
        print(f"Description: {desc}")
        print(f"Created: {created_at}")
        if metadata:
            meta = json.loads(metadata)
            print(f"Metadata: {json.dumps(meta, indent=2)}")

    # Query counts by model
    print(f"\n{'='*70}")
    print("QUERIES BY MODEL")
    print("="*70)
    cursor.execute("""
        SELECT model_name,
               COUNT(*) as total,
               SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
               SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
        FROM queries
        GROUP BY model_name
    """)
    for row in cursor.fetchall():
        model, total, successful, failed = row
        print(f"{model}: {successful}/{total} successful ({failed} failed)")

    # Think block analysis
    print(f"\n{'='*70}")
    print("THINK BLOCK USAGE")
    print("="*70)
    cursor.execute("""
        SELECT model_name,
               COUNT(*) as total_queries,
               SUM(CASE WHEN think_block != '' THEN 1 ELSE 0 END) as with_think,
               AVG(LENGTH(think_block)) as avg_think_length
        FROM queries
        GROUP BY model_name
    """)
    for row in cursor.fetchall():
        model, total, with_think, avg_length = row
        pct = (with_think / total * 100) if total > 0 else 0
        print(f"{model}:")
        print(f"  Think blocks: {with_think}/{total} ({pct:.1f}%)")
        print(f"  Avg think length: {avg_length:.0f} chars")

    # Response time analysis
    print(f"\n{'='*70}")
    print("RESPONSE TIME ANALYSIS")
    print("="*70)
    cursor.execute("""
        SELECT model_name,
               AVG(elapsed_seconds) as avg_time,
               MIN(elapsed_seconds) as min_time,
               MAX(elapsed_seconds) as max_time
        FROM queries
        WHERE success = 1
        GROUP BY model_name
    """)
    for row in cursor.fetchall():
        model, avg_time, min_time, max_time = row
        print(f"{model}:")
        print(f"  Average: {avg_time:.2f}s")
        print(f"  Range: {min_time:.2f}s - {max_time:.2f}s")

    # Response length analysis
    print(f"\n{'='*70}")
    print("RESPONSE LENGTH ANALYSIS")
    print("="*70)
    cursor.execute("""
        SELECT model_name,
               AVG(LENGTH(content)) as avg_content_length,
               MIN(LENGTH(content)) as min_length,
               MAX(LENGTH(content)) as max_length
        FROM queries
        WHERE success = 1
        GROUP BY model_name
    """)
    for row in cursor.fetchall():
        model, avg_len, min_len, max_len = row
        print(f"{model}:")
        print(f"  Average: {avg_len:.0f} chars")
        print(f"  Range: {min_len} - {max_len} chars")

    # Questions answered
    print(f"\n{'='*70}")
    print("QUESTIONS")
    print("="*70)
    cursor.execute("""
        SELECT tags_json, COUNT(DISTINCT model_name) as models_answered
        FROM queries
        WHERE tags_json LIKE '%Q0%'
        GROUP BY tags_json
    """)
    question_ids = set()
    for row in cursor.fetchall():
        tags_json, count = row
        tags = json.loads(tags_json)
        q_id = next((t for t in tags if t.startswith('Q')), None)
        if q_id:
            question_ids.add(q_id)
            print(f"{q_id}: answered by {count} model(s)")

    print(f"\nTotal questions: {len(question_ids)}")

    conn.close()

    print(f"\n{'='*70}")
    print("Analysis complete!")
    print(f"{'='*70}\n")


def find_latest_db(results_dir: Path) -> Path | None:
    """Return the most recently modified run_*.db in results_dir, or None."""
    db_files = list(results_dir.glob("run_*.db"))
    if not db_files:
        return None
    return max(db_files, key=lambda p: p.stat().st_mtime)


def main():
    """Entry point — resolve DB path and run analysis."""
    parser = argparse.ArgumentParser(description="Analyze study results")
    parser.add_argument("--experiment", metavar="ID", help="Experiment ID under experiments/")
    parser.add_argument("db", nargs="?", help="Path to specific .db file (optional)")
    args = parser.parse_args()

    if args.db:
        analyze_study(args.db)
        return

    if args.experiment:
        results_dir = Path("experiments") / args.experiment / "results"
        if not results_dir.exists():
            print(f"Error: experiments/{args.experiment}/results/ not found")
            sys.exit(1)
        db_path = find_latest_db(results_dir)
        if not db_path:
            print(f"No run_*.db files found in experiments/{args.experiment}/results/")
            sys.exit(1)
        print(f"Using most recent run: {db_path}\n")
        analyze_study(str(db_path))
        return

    # Legacy fallback — look in top-level results/
    results_dir = Path("results")
    if results_dir.exists():
        db_path = find_latest_db(results_dir)
        if db_path:
            print(f"Using most recent database: {db_path}\n")
            analyze_study(str(db_path))
        else:
            print("No database files found in results/")
            print(f"Usage: python {sys.argv[0]} --experiment <id>")
    else:
        print("No results directory found")
        print(f"Usage: python {sys.argv[0]} --experiment <id>")


if __name__ == "__main__":
    main()
