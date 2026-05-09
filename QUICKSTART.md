# Quick Start Guide

## Installation

**First time setup:**
```bash
cd ~/AI-Development/psych_llm_study
./setup.sh
```

**Activate environment:**
```bash
source .venv/bin/activate
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Running Your First Study

### 1. Verify your setup

Check that models are available:
```bash
cat models.json
```

Check your questions:
```bash
cat questions.json
```

### 2. Run the study

```bash
python run_study.py
```

You'll see output like:
```
Loading configurations...

Study ID: pilot-2026-05
Description: Pilot study examining LLM reasoning patterns in psychology domains
Questions: 5
Models: 4
Total queries: 20

Results will be saved to: results/study_2026-05-09_14-30-15.db

Starting study...

======================================================================
Testing model: grok-4.20-0309-reasoning
======================================================================
  ✓ Model available: Connected to xai
  
  [1/20] Q01 (moral_reasoning)
  Question: Is it ever acceptable to lie to protect someone's feelings? Explain your...
  ✓ Response received (2.34s, think: ✓)
  Answer: While honesty is generally valued, there are nuanced situations where protect...
  Think: <considering the ethical framework> This involves weighing consequentialist...
...
```

### 3. Analyze results

Run the analysis script:
```bash
python scripts/analyze_results.py
```

Or specify a database:
```bash
python scripts/analyze_results.py results/study_2026-05-09_14-30-15.db
```

### 4. Query the database directly

```bash
sqlite3 results/study_2026-05-09_14-30-15.db
```

```sql
.mode column
.headers on

-- See all responses for Q01
SELECT model_name, content 
FROM queries 
WHERE tags_json LIKE '%Q01%';

-- Find models that use think blocks
SELECT DISTINCT model_name, COUNT(*) as think_count
FROM queries 
WHERE think_block != ''
GROUP BY model_name;

-- Compare response times
SELECT model_name, AVG(elapsed_seconds) as avg_time
FROM queries
GROUP BY model_name
ORDER BY avg_time;
```

## Customizing Your Study

### Add your own questions

Edit `questions.json`:
```json
{
  "study_id": "my-study-2026",
  "description": "My custom study",
  "questions": [
    {
      "id": "Q01",
      "category": "your_category",
      "prompt": "Your question here?",
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

### Change models

Edit `models.json`:
```json
{
  "models": [
    "your-model-name",
    "another-model"
  ],
  "probe_models_path": "/Users/toddfirsich/AI-Development/llm-model-update/probes/probe_models.json"
}
```

### Re-run with new configuration

```bash
python scripts/run_study.py
```

Each run creates a new timestamped database, so you never overwrite previous results.

## Sharing Your Research

To share your study setup with others:

1. Commit your `questions.json` and `models.json` to git
2. Push to GitHub
3. Others can clone and run: `python scripts/run_study.py`

The `.gitignore` excludes `results/` so raw data stays local unless you explicitly share it.

## Python Analysis

```python
import sqlite3
import pandas as pd
import json

# Load results
conn = sqlite3.connect('results/study_2026-05-09_14-30-15.db')
df = pd.read_sql_query("SELECT * FROM queries", conn)

# Parse tags
df['tags'] = df['tags_json'].apply(json.loads)

# Filter by question
q01_df = df[df['tags'].apply(lambda x: 'Q01' in x)]

# Compare models
print(q01_df.groupby('model_name')['content'].first())

# Analyze think blocks
think_df = df[df['think_block'] != '']
print(f"Models with think blocks: {think_df['model_name'].unique()}")
```

## Troubleshooting

**Model not found:**
- Check that the model exists in your `probe_models.json`
- Verify the model name matches exactly

**Backend unavailable:**
- For cloud models: check API keys in `~/.env`
- For local models: ensure Ollama/llama.cpp is running

**Empty results:**
- Check the terminal output for error messages
- Verify at least one model completed successfully

## Next Steps

- Modify questions for your research domain
- Add more models to compare
- Run analysis scripts on your results
- Share your question sets with colleagues
