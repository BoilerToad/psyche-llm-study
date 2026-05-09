# Psychology LLM Study

A research framework for systematically querying multiple LLMs with psychology-related questions and tracking both their final answers and reasoning processes (think blocks).

## Overview

This project uses the `llm-client` package to:
- Ask standardized questions across multiple LLMs
- Capture both final answers and intermediate reasoning (think blocks)
- Log all interactions to SQLite for analysis
- Support reproducible research with version-controlled questions and model configurations

## Installation

### Quick Install (Recommended)

```bash
cd ~/AI-Development/psych_llm_study
./setup.sh
```

The setup script will:
1. Clone llm-client from GitHub (if not present)
2. Create a virtual environment
3. Install all dependencies
4. Verify the installation

### Manual Installation

See [INSTALL.md](INSTALL.md) for detailed step-by-step instructions.

### For New Users

If you're cloning this project for the first time:

```bash
# Clone this repository
git clone https://github.com/YourUsername/psych_llm_study.git
cd psych_llm_study

# Run setup (will clone llm-client automatically)
./setup.sh

# Activate environment
source .venv/bin/activate
```

## Quick Start

1. **Verify installation:**
   ```bash
   source .venv/bin/activate
   python tests/verify_setup.py
   ```

2. **Test model connectivity:**
   ```bash
   python tests/test_models.py              # Test all models
   python tests/test_models.py --backend ollama  # Test local models only
   ```

3. **Configure your questions** in `questions.json`

4. **Run the study:**
   ```bash
   python scripts/run_study.py
   ```

Results are saved to `results/study_TIMESTAMP.db` with full SQLite logging.

## File Structure

```
psych_llm_study/
├── pyproject.toml          # Project configuration
├── questions.json          # Questions to ask (version controlled)
├── models.json             # Full model registry (60+ models)
├── scripts/                # Main operational scripts
│   ├── new_experiment.py   # Scaffold a new experiment folder
│   ├── run_study.py        # Experiment runner (independent questions)
│   ├── run_study_chain.py  # Experiment runner (chained questions)
│   ├── analyze_results.py  # Results analysis tool
│   └── judge_responses.py  # LLM judge analysis of responses
├── tests/                  # Setup verification and tests
│   ├── verify_setup.py     # Installation verification
│   └── test_models.py      # Model connectivity tester
├── logs/                   # Test logs with raw API responses
├── results/                # SQLite databases (not in git)
├── README.md               # This file
└── .gitignore              # Excludes results/ and logs/
```

## questions.json Format

```json
{
  "study_id": "pilot-2026-05",
  "description": "Pilot study on moral reasoning",
  "questions": [
    {
      "id": "Q01",
      "category": "moral_reasoning",
      "prompt": "Is it ever acceptable to lie to protect someone's feelings?",
      "tags": ["ethics", "deception", "prosocial"]
    },
    {
      "id": "Q02",
      "category": "theory_of_mind",
      "prompt": "If someone believes the Earth is flat, how would you explain their perspective?",
      "tags": ["perspective_taking", "belief"]
    }
  ]
}
```

## models.json Format

`models.json` contains the **full model registry** (60+ models) with complete metadata:

```json
{
  "_meta": {
    "version": "1.0",
    "description": "Model registry - single source of truth for all LLM backends"
  },
  "models": [
    {
      "name": "grok-4.20-0309-reasoning",
      "backend": "xai",
      "family": "grok",
      "think_blocks": true,
      "geopolitical_origin": "US/xAI",
      "enabled": true
    },
    {
      "name": "gemma4:31b-cloud",
      "backend": "ollama_cloud",
      "family": "gemma4",
      "size_gb": 18,
      "geopolitical_origin": "US/Google",
      "enabled": true
    }
  ]
}
```

All models in the registry are available. Use `enabled: false` to skip models without deleting them.

## Output

Each study run creates a timestamped SQLite database in `results/`:

```
results/study_2026-05-09_14-30-15.db
```

### Query the results

```bash
sqlite3 results/study_2026-05-09_14-30-15.db
```

```sql
-- See all responses
SELECT model_name, prompt, content, think_block, elapsed_seconds 
FROM queries;

-- Compare responses by question
SELECT model_name, content 
FROM queries 
WHERE tags_json LIKE '%Q01%';

-- Find models with think blocks
SELECT DISTINCT model_name 
FROM queries 
WHERE think_block != '';

-- Average response time by model
SELECT model_name, AVG(elapsed_seconds) as avg_time
FROM queries 
GROUP BY model_name;
```

## Tracked Data

For each question × model combination:
- **Prompt**: Exact question text
- **Content**: Final answer (think blocks stripped)
- **Think block**: Intermediate reasoning (for reasoning models)
- **Elapsed time**: Response latency
- **Success status**: Whether the query succeeded
- **Raw response**: Full JSON from the LLM
- **Tags**: Question ID, category, and custom tags
- **Metadata**: Model name, backend, timestamp

## Testing Model Connectivity

Before running a study, test which models are accessible:

```bash
# Test all enabled models (60+)
python tests/test_models.py

# Filter by backend
python tests/test_models.py --backend ollama       # Local ollama models
python tests/test_models.py --backend ollama_cloud # Ollama cloud models
python tests/test_models.py --backend xai          # xAI (Grok)
python tests/test_models.py --backend llamacpp     # llama.cpp server

# Filter by model family
python tests/test_models.py --family llama         # All llama models
python tests/test_models.py --family grok          # All grok models
python tests/test_models.py --family deepseek      # All deepseek models
```

**Features:**
- Tests health check and simple query for each model
- Logs raw API responses to `logs/model_test_TIMESTAMP.log`
- Provides detailed summary with troubleshooting recommendations
- Shows token counts, timing, and think block support

## Reproducibility

To reproduce a study:

1. Clone this repository
2. Run: `./setup.sh` (auto-installs llm-client)
3. Activate environment: `source .venv/bin/activate`
4. Test models: `python tests/test_models.py`
5. Run: `python scripts/run_study.py`

All questions and model configurations are version controlled, so others can replicate your exact experimental setup.

## Example Analysis Workflow

```python
import sqlite3
import pandas as pd

# Load results
conn = sqlite3.connect('results/study_2026-05-09_14-30-15.db')
df = pd.read_sql_query("SELECT * FROM queries", conn)

# Analyze think block usage
print(df[df['think_block'] != ''].groupby('model_name').size())

# Compare response lengths
df['content_length'] = df['content'].str.len()
print(df.groupby('model_name')['content_length'].mean())
```

## Contributing

This framework is designed to be reusable. To adapt for your research:

1. Modify `questions.json` with your questions
2. Update `models.json` with your target models
3. Optionally extend scripts in `scripts/` for custom analysis
4. Share your `questions.json` for reproducibility

## API Keys

Set required API keys in `~/.env`:

```bash
# For xAI models (Grok)
XAI_API_KEY=your_xai_api_key

# For Ollama cloud models
OLLAMA_API_KEY=your_ollama_api_key
```

Local models (ollama, llamacpp) don't require API keys.

## Logs and Debugging

All test runs create detailed logs in `logs/`:
- Raw API responses in JSON format
- Token counts and timing data
- Error messages and stack traces
- Think blocks for reasoning models

Use these logs to:
- Debug API connection issues
- Understand model behavior
- Verify response formats
- Track token usage

## Project Structure

```
psych_llm_study/
├── scripts/                # Operational scripts (run studies, analyze results)
│   ├── run_study.py        # Main experiment runner
│   └── analyze_results.py  # Results analysis
├── tests/                  # Verification and testing tools
│   ├── verify_setup.py     # Installation verification
│   └── test_models.py      # Model connectivity tester
├── results/                # SQLite databases (gitignored)
├── logs/                   # Test logs with raw responses (gitignored)
├── questions.json          # Study questions (version controlled)
├── models.json             # Full model registry (version controlled)
├── setup.sh                # Automated installation script
└── [docs and configs]
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

This project is open source and freely available for research and educational purposes.
