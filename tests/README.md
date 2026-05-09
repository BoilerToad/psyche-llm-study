# Tests

This directory contains test and verification scripts for the Psychology LLM Study framework.

## Available Tests

### `verify_setup.py`
Comprehensive setup verification script that checks all installation requirements.

**Usage:**
```bash
python tests/verify_setup.py
```

**What it checks:**
- Python version (≥ 3.13)
- llm_client package import
- Configuration files exist
- probe_models.json path is valid
- Virtual environment is active

**When to run:**
- After initial installation
- After updating dependencies
- When troubleshooting installation issues
- Before running studies (optional)

## Adding Tests

As the project grows, you may want to add:

### Unit Tests
Test individual components:
```python
# tests/test_config_loader.py
import json
from pathlib import Path

def test_load_questions():
    """Test that questions.json loads correctly."""
    with open("questions.json") as f:
        data = json.load(f)
    assert "questions" in data
    assert len(data["questions"]) > 0
```

### Integration Tests
Test end-to-end workflows:
```python
# tests/test_study_run.py
def test_single_model_query():
    """Test querying a single model with one question."""
    # Create client, run query, verify response
    pass
```

### Validation Tests
Validate configuration files:
```python
# tests/test_config_validation.py
def test_questions_schema():
    """Validate questions.json has required fields."""
    pass
```

## Running Tests with pytest

If you add pytest-based tests:

```bash
# Install pytest
pip install pytest

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_config_loader.py
```

## Test Design Guidelines

When adding tests:

1. **Descriptive names:** `test_load_questions_with_valid_json()`
2. **Independent:** Each test should run standalone
3. **Fast:** Keep tests quick (mock external services)
4. **Clear assertions:** Test one thing per test
5. **Fixtures:** Use pytest fixtures for common setup
6. **Documentation:** Docstring explaining what's tested

## Current Test Coverage

- ✅ Setup verification (Python, packages, config files)
- ⬜ Unit tests for configuration loading
- ⬜ Integration tests for study runs
- ⬜ Mock tests for LLM queries
- ⬜ Validation tests for JSON schemas
