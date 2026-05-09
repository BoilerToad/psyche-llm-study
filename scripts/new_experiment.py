#!/usr/bin/env python3
"""
new_experiment.py
─────────────────
Scaffold a new experiment folder under experiments/<id>/.

Creates:
  experiments/<id>/experiment.json      — metadata and run config
  experiments/<id>/exp_questions.json   — frozen copy of questions.json
  experiments/<id>/exp_models.json      — frozen subset of models.json
  experiments/<id>/results/             — results go here

Usage:
    python scripts/new_experiment.py --id pilot-01 --name "Moral Reasoning Pilot"
    python scripts/new_experiment.py --id pilot-01 --name "..." --models "grok-3,gemma4:31b-cloud"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    """Scaffold a new experiment folder under experiments/<id>/."""
    parser = argparse.ArgumentParser(description="Scaffold a new experiment folder")
    parser.add_argument("--id", required=True, dest="exp_id",
                        help="Experiment ID (used as folder name)")
    parser.add_argument("--name", required=True, help="Human-readable experiment name")
    parser.add_argument("--description", default="", help="Experiment description")
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated model names to include (default: all enabled models)",
    )
    args = parser.parse_args()

    exp_dir = Path("experiments") / args.exp_id
    if exp_dir.exists():
        print(f"Error: experiments/{args.exp_id}/ already exists")
        sys.exit(1)

    # Load globals
    with open("models.json", "r", encoding="utf-8") as f:
        models_registry = json.load(f)
    with open("questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    # Filter models
    all_models = [m for m in models_registry.get("models", []) if m.get("enabled", True)]
    if args.models:
        selected_names = {n.strip() for n in args.models.split(",")}
        selected = [m for m in all_models if m["name"] in selected_names]
        missing = selected_names - {m["name"] for m in selected}
        if missing:
            print(f"Warning: models not found in registry: {', '.join(sorted(missing))}")
    else:
        selected = all_models

    # exp_models.json — same schema as models.json, filtered subset
    exp_models = {
        "_meta": {
            **models_registry.get("_meta", {}),
            "experiment_id": args.exp_id,
            "sourced_from": "models.json",
            "sourced_at": datetime.now().isoformat(),
        },
        "models": selected,
    }

    # experiment.json
    experiment = {
        "experiment_id": args.exp_id,
        "name": args.name,
        "description": args.description,
        "version": "1.0",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "questions_file": "exp_questions.json",
        "models_file": "exp_models.json",
        "run_config": {
            "timeout": 240,
            "temperature": 0.7,
        },
    }

    # Write files
    exp_dir.mkdir(parents=True)
    (exp_dir / "results").mkdir()

    with open(exp_dir / "experiment.json", "w", encoding="utf-8") as f:
        json.dump(experiment, f, indent=2)

    with open(exp_dir / "exp_questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2)

    with open(exp_dir / "exp_models.json", "w", encoding="utf-8") as f:
        json.dump(exp_models, f, indent=2)

    n_questions = len(questions.get("questions", []))
    print(f"Created: experiments/{args.exp_id}/")
    print("  experiment.json    — metadata and run config")
    print(f"  exp_questions.json — {n_questions} questions")
    print(f"  exp_models.json    — {len(selected)} models")
    print("  results/           — run outputs will go here")
    print("\nTo run:")
    print(f"  python scripts/run_study.py --experiment {args.exp_id}")


if __name__ == "__main__":
    main()
