#!/usr/bin/env python3
"""
run_study.py
────────────
Main experiment runner for psychology LLM study.

Usage:
    python scripts/run_study.py --experiment <id>   # recommended
    python scripts/run_study.py                      # legacy: uses questions.json + models.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from llm_client import LLMClient, create_logger


def load_json(path: Path) -> dict:
    """Load and return JSON from path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_study():  # pylint: disable=too-many-locals,too-many-statements
    """Execute the psychology study across all models and questions."""

    parser = argparse.ArgumentParser(description="Run psychology LLM study")
    parser.add_argument("--experiment", metavar="ID", help="Experiment ID under experiments/")
    args = parser.parse_args()

    if args.experiment:
        exp_dir = Path("experiments") / args.experiment
        if not exp_dir.exists():
            print(f"Error: experiments/{args.experiment}/ not found")
            print("Create it first: python scripts/new_experiment.py "
                  f"--id {args.experiment} --name '...'")
            return

        experiment = load_json(exp_dir / "experiment.json")
        questions_config = load_json(exp_dir / experiment["questions_file"])
        models_config = load_json(exp_dir / experiment["models_file"])
        models_file = str(exp_dir / experiment["models_file"])
        results_dir = exp_dir / "results"
        run_config = experiment.get("run_config", {})
        timeout = run_config.get("timeout", 240)

        print(f"Experiment: {experiment['name']} ({args.experiment})")
    else:
        # Legacy mode — uses top-level globals
        questions_config = load_json(Path("questions.json"))
        models_config = load_json(Path("models.json"))
        models_file = "models.json"
        results_dir = Path("results")
        timeout = 240

    study_id = questions_config.get("study_id", "unknown")
    description = questions_config.get("description", "")
    questions = questions_config.get("questions", [])

    all_models = models_config.get("models", [])
    enabled_models = [m for m in all_models if m.get("enabled", True)]
    model_names = [m["name"] for m in enabled_models]

    print(f"Study ID: {study_id}")
    print(f"Description: {description}")
    print(f"Questions: {len(questions)}")
    print(f"Models: {len(model_names)}")
    print(f"Total queries: {len(questions) * len(model_names)}")

    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    db_path = results_dir / f"run_{timestamp}.db"

    print(f"\nResults will be saved to: {db_path}")
    print("\nStarting study...\n")

    logger = create_logger(
        backend="sqlite",
        path=str(db_path),
        experiment_id=study_id,
        experiment_name=description,
    )

    total_queries = len(questions) * len(model_names)
    current_query = 0

    for model_name in model_names:
        print(f"\n{'='*70}")
        print(f"Testing model: {model_name}")
        print(f"{'='*70}")

        try:
            client = LLMClient(
                models_file=models_file,
                model=model_name,
                logger=logger,
            )

            ok, detail = client.health_check()
            if not ok:
                print(f"  ⚠️  Model unavailable: {detail}")
                print(f"  Skipping all questions for {model_name}")
                continue

            print(f"  ✓ Model available: {detail}")

            for question in questions:
                current_query += 1
                q_id = question.get("id", "?")
                category = question.get("category", "unknown")
                prompt = question.get("prompt", "")
                tags = [q_id, category] + question.get("tags", [])

                print(f"\n  [{current_query}/{total_queries}] {q_id} ({category})")
                print(f"  Question: {prompt[:80]}...")

                result = client.chat(prompt, tags=tags, timeout=timeout)

                if result.success:
                    has_think = "✓" if result.think_block else "✗"
                    print(f"  ✓ Response received ({result.elapsed_s:.2f}s, think: {has_think})")
                    print(f"  Answer: {result.content[:100]}...")
                    if result.think_block:
                        print(f"  Think: {result.think_block[:80]}...")
                else:
                    print(f"  ✗ Query failed: {result.error}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"  ✗ Error with model {model_name}: {e}")
            continue

    logger.close()

    print(f"\n{'='*70}")
    print("Study complete!")
    print(f"{'='*70}")
    print(f"\nResults saved to: {db_path}")
    print("\nExample queries:")
    print(f"  sqlite3 {db_path}")
    print("  SELECT model_name, COUNT(*) FROM queries GROUP BY model_name;")
    print("  SELECT * FROM queries WHERE tags_json LIKE '%Q01%';")
    print("  SELECT model_name, content FROM queries WHERE think_block != '';")


if __name__ == "__main__":
    run_study()
