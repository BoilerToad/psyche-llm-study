# Scripts

This directory contains the main operational scripts for the Psychology LLM Study framework.

## Available Scripts

### `run_study.py`
Main experiment runner that systematically queries all models with all questions and logs results to SQLite.

**Usage:**
```bash
python scripts/run_study.py
```

**What it does:**
- Loads questions from `questions.json`
- Loads models from `models.json`
- Queries each model with each question
- Logs all responses (including think blocks) to SQLite
- Creates timestamped database in `results/`

### `analyze_results.py`
Results analysis script that provides summary statistics and insights from study databases.

**Usage:**
```bash
# Analyze most recent study
python scripts/analyze_results.py

# Analyze specific database
python scripts/analyze_results.py results/study_2026-05-09_14-30-15.db
```

**What it shows:**
- Study metadata
- Query counts by model
- Think block usage statistics
- Response time analysis
- Response length analysis
- Question coverage

## Adding New Scripts

Future scripts that may be added to this directory:

- `add_models.py` - Interactive tool to add models to `models.json`
- `add_questions.py` - Interactive tool to add questions to `questions.json`
- `compare_studies.py` - Compare results across multiple study runs
- `export_results.py` - Export study results to CSV, Excel, or other formats
- `summarize_sweep.py` - Generate summary reports for model sweeps

## Script Design Guidelines

When adding new scripts:

1. **Make them executable:** `chmod +x scripts/your_script.py`
2. **Add shebang:** `#!/usr/bin/env python3`
3. **Include docstring:** Clear description and usage examples
4. **Run from project root:** Scripts should be run as `python scripts/script_name.py`
5. **Use relative paths:** Reference config files relative to project root
6. **Accept arguments:** Use `sys.argv` or `argparse` for flexibility
7. **Provide helpful output:** Show progress, errors, and results clearly
