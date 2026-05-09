#!/usr/bin/env python3
"""
run_study_chain.py
──────────────────
Chained experiment runner. Each question can reference a prior question's
response, enabling genuine adversarial follow-ups across 2, 3, or more turns.

To chain a question, add "chain_from": "<question_id>" to its entry in
exp_questions.json. The referenced model's response is prepended to the
prompt before it is sent. Questions without "chain_from" behave identically
to run_study.py.

Chain structure is printed at startup so you can verify the sequence.
The full chained prompt (including the injected prior response) is what
gets stored in SQLite — the DB is a complete reproduction record.

Usage:
    python scripts/run_study_chain.py --experiment newcomb-2026-05

exp_questions.json example:
    {"id": "Q01", "prompt": "...", "tags": [...]}
    {"id": "Q02", "prompt": "...", "chain_from": "Q01", "tags": [...]}
    {"id": "Q03", "prompt": "...", "chain_from": "Q02", "tags": [...]}
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from llm_client import LLMClient, create_logger


CHAIN_PREFIX = (
    "Your previous response was:\n\n"
    "{previous_response}\n\n"
    "---\n\n"
)


def load_json(path: Path) -> dict:
    """Load and return JSON from path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_chained_prompt(question, prior_responses):
    """Return the prompt with prior answer prepended if chain_from is set."""
    chain_from = question.get("chain_from")
    if not chain_from:
        return question["prompt"]
    prior = prior_responses.get(chain_from)
    if not prior:
        return question["prompt"]
    return CHAIN_PREFIX.format(previous_response=prior) + question["prompt"]


def print_chain_structure(questions):
    """Print the chain dependency graph for the question set."""
    print("\nChain structure:")
    for q in questions:
        chain_from = q.get("chain_from")
        if chain_from:
            print(f"  {chain_from} → {q['id']}")
        else:
            print(f"  {q['id']} (independent)")


def run_study_chain():  # pylint: disable=too-many-locals,too-many-statements
    """Execute a chained study, injecting prior responses into follow-up prompts."""

    parser = argparse.ArgumentParser(description="Run chained psychology LLM study")
    parser.add_argument("--experiment", metavar="ID", required=True,
                        help="Experiment ID under experiments/")
    args = parser.parse_args()

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

    study_id = questions_config.get("study_id", "unknown")
    description = questions_config.get("description", "")
    questions = questions_config.get("questions", [])

    enabled_models = [m for m in models_config.get("models", []) if m.get("enabled", True)]
    model_names = [m["name"] for m in enabled_models]

    print(f"Experiment: {experiment['name']} ({args.experiment})")
    print(f"Study ID:   {study_id}")
    print(f"Questions:  {len(questions)}")
    print(f"Models:     {len(model_names)}")
    print(f"Queries:    {len(questions) * len(model_names)}")
    print_chain_structure(questions)

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
        print(f"Model: {model_name}")
        print(f"{'='*70}")

        prior_responses = {}  # q_id -> content, accumulated per model

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
                current_query += len(questions)
                continue

            print(f"  ✓ Model available: {detail}")

            for question in questions:
                current_query += 1
                q_id = question.get("id", "?")
                category = question.get("category", "unknown")
                tags = [q_id, category] + question.get("tags", [])
                chain_from = question.get("chain_from")

                print(f"\n  [{current_query}/{total_queries}] {q_id} ({category})")

                if chain_from:
                    has_prior = chain_from in prior_responses
                    status = "✓ available" if has_prior else "✗ missing — sending bare prompt"
                    print(f"  Chained from {chain_from}: {status}")

                prompt = build_chained_prompt(question, prior_responses)
                result = client.chat(prompt, tags=tags, timeout=timeout)

                if result.success:
                    prior_responses[q_id] = result.content
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
    print("  SELECT model_name, content FROM queries WHERE tags_json LIKE '%Q01%';")
    print("  SELECT model_name, content FROM queries WHERE tags_json LIKE '%Q02%';")


if __name__ == "__main__":
    run_study_chain()
