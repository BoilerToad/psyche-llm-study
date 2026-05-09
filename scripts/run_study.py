#!/usr/bin/env python3
"""
run_study.py
────────────
Main experiment runner for psychology LLM study.

Loads questions from questions.json, models from models.json,
and systematically queries each model with each question while
logging full responses (including think blocks) to SQLite.
"""

import json
from datetime import datetime
from pathlib import Path

from llm_client import LLMClient, create_logger


def load_questions(path: str = "questions.json") -> dict:
    """Load questions configuration from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_models(path: str = "models.json") -> dict:
    """Load models configuration from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_study():
    """Execute the psychology study across all models and questions."""
    
    # Load configurations
    print("Loading configurations...")
    questions_config = load_questions()
    models_config = load_models()
    
    study_id = questions_config.get("study_id", "unknown")
    description = questions_config.get("description", "")
    questions = questions_config.get("questions", [])
    models = models_config.get("models", [])
    probe_models_path = models_config.get("probe_models_path")
    
    print(f"\nStudy ID: {study_id}")
    print(f"Description: {description}")
    print(f"Questions: {len(questions)}")
    print(f"Models: {len(models)}")
    print(f"Total queries: {len(questions) * len(models)}")
    
    # Create results directory if it doesn't exist
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    # Create timestamped database
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    db_path = results_dir / f"study_{timestamp}.db"
    
    print(f"\nResults will be saved to: {db_path}")
    print("\nStarting study...\n")
    
    # Create logger
    logger = create_logger(
        backend="sqlite",
        path=str(db_path),
        experiment_id=study_id,
        experiment_name=description,
    )
    
    # Run the study
    total_queries = len(questions) * len(models)
    current_query = 0
    
    for model_name in models:
        print(f"\n{'='*70}")
        print(f"Testing model: {model_name}")
        print(f"{'='*70}")
        
        try:
            # Create client for this model
            client = LLMClient(
                models_file=probe_models_path,
                model=model_name,
                logger=logger,
            )
            
            # Check if model is available
            ok, detail = client.health_check()
            if not ok:
                print(f"  ⚠️  Model unavailable: {detail}")
                print(f"  Skipping all questions for {model_name}")
                continue
            
            print(f"  ✓ Model available: {detail}")
            
            # Ask each question
            for question in questions:
                current_query += 1
                q_id = question.get("id", "?")
                category = question.get("category", "unknown")
                prompt = question.get("prompt", "")
                tags = [q_id, category] + question.get("tags", [])
                
                print(f"\n  [{current_query}/{total_queries}] {q_id} ({category})")
                print(f"  Question: {prompt[:80]}...")
                
                # Query the model
                result = client.chat(prompt, tags=tags)
                
                if result.success:
                    has_think = "✓" if result.think_block else "✗"
                    print(f"  ✓ Response received ({result.elapsed_s:.2f}s, think: {has_think})")
                    print(f"  Answer: {result.content[:100]}...")
                    if result.think_block:
                        print(f"  Think: {result.think_block[:80]}...")
                else:
                    print(f"  ✗ Query failed: {result.error}")
        
        except Exception as e:
            print(f"  ✗ Error with model {model_name}: {e}")
            continue
    
    # Close logger
    logger.close()
    
    print(f"\n{'='*70}")
    print("Study complete!")
    print(f"{'='*70}")
    print(f"\nResults saved to: {db_path}")
    print("\nQuery results:")
    print(f"  sqlite3 {db_path}")
    print("\nExample queries:")
    print("  SELECT model_name, COUNT(*) FROM queries GROUP BY model_name;")
    print("  SELECT * FROM queries WHERE tags_json LIKE '%Q01%';")
    print("  SELECT model_name, content FROM queries WHERE think_block != '';")


if __name__ == "__main__":
    run_study()
