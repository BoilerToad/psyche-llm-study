# psych_llm_study — Claude Code Instructions

This file is auto-loaded at the start of every session. Follow all rules here without being asked.

---

## Project Overview

A research framework for querying multiple LLMs with psychology questions and capturing responses (including think blocks) in SQLite for analysis. Key scripts are in `scripts/`, tests in `tests/`, experiments under `experiments/<id>/`.

---

## Change Checklist

Run through this checklist for **every** code fix, update, or enhancement — no exceptions and no need for the user to ask.

### 1. Tests

- If you changed any script in `scripts/`, check whether `tests/verify_setup.py` or `tests/test_models.py` need updating (e.g., new CLI flags, changed paths, updated workflow steps).
- Run pylint on every Python file you touched:
  ```bash
  source .venv/bin/activate && pylint <file>
  ```
- Run pytest if tests exist:
  ```bash
  source .venv/bin/activate && pytest tests/
  ```
- Fix all pylint errors before reporting work as done. Warnings are acceptable if unavoidable — document why.

### 2. Documentation

- If the CLI interface changed (new flags, new scripts, changed defaults), update `README.md`.
- If the folder structure changed, update both `README.md` and the file tree diagrams in `ENHANCEMENTS`.
- If a new script was added, add it to the `scripts/` section of `README.md` with a one-line description and usage example.

### 3. ENHANCEMENTS file

- When implementing an enhancement from `ENHANCEMENTS`, update its **Status** line:
  - `Proposed` → `Implemented — <script path>` when complete
  - `In Progress` if partially done across sessions
- Do not close an enhancement as implemented unless all listed scripts changes are done.

### 4. Git

- After completing any meaningful unit of work, commit to git with a clear, descriptive message.
- Stage only the files relevant to the change — do not use `git add -A` blindly.
- Push to GitHub unless the user says otherwise.
- Commit message format:
  ```
  <verb> <what>: <one-line reason>

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  ```

---

## Project-Specific Conventions

### Experiments

- Experiments live under `experiments/<id>/` with three frozen files: `experiment.json`, `exp_questions.json`, `exp_models.json`.
- Results go in `experiments/<id>/results/run_TIMESTAMP.db`.
- Judge analysis output goes in `experiments/<id>/analysis/judge_TIMESTAMP.md`.
- Never modify `exp_*` files in an existing experiment — they are the replication record.

### Models

- `models.json` is the single source of truth for all model metadata.
- To disable a model without deleting it, set `"enabled": false`.
- `exp_models.json` in an experiment is a frozen subset — changes to `models.json` do not backfill existing experiments.

### Default timeout

All `client.chat()` calls use `timeout=240` unless overridden by `experiment.json` `run_config`.

### Judge model

Default judge for `judge_responses.py` is `mistral-large-3:675b-cloud`. Override with `--judge`.

---

## File Map

```
psych_llm_study/
├── CLAUDE.md                        # this file — auto-loaded by Claude Code
├── ENHANCEMENTS                     # enhancement backlog and status
├── README.md                        # user-facing documentation
├── models.json                      # global model registry
├── questions.json                   # global question bank
├── experiments/
│   └── <id>/
│       ├── experiment.json
│       ├── exp_questions.json
│       ├── exp_models.json
│       ├── results/run_*.db
│       └── analysis/judge_*.md
├── scripts/
│   ├── new_experiment.py            # scaffold a new experiment
│   ├── run_study.py                 # run an experiment
│   ├── analyze_results.py           # basic SQL analysis of results
│   └── judge_responses.py           # LLM judge analysis of responses
└── tests/
    ├── verify_setup.py              # installation verification
    └── test_models.py               # model connectivity sweep
```
