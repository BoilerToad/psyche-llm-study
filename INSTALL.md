# Installation Guide

This guide will help you set up the Psychology LLM Study framework on your machine.

## Prerequisites

- Python 3.13 or higher
- Git
- Internet connection (for cloning repositories and downloading dependencies)

## Quick Install (Automated)

```bash
cd ~/AI-Development/psych_llm_study
./setup.sh
```

The script will automatically:
- Clone llm-client from GitHub if needed
- Create a virtual environment
- Install all dependencies
- Verify the installation

## Manual Installation

If you prefer to set up manually or the automated script doesn't work for your system, follow these steps:

### Step 1: Clone the repositories

```bash
# Create a directory for your projects
mkdir -p ~/AI-Development
cd ~/AI-Development

# Clone this repository
git clone https://github.com/YourUsername/psych_llm_study.git

# Clone llm-client (required dependency)
git clone https://github.com/BoilerToad/llm-client.git
```

Your directory structure should look like:
```
~/AI-Development/
├── psych_llm_study/
└── llm-client/
```

### Step 2: Create a virtual environment

```bash
cd ~/AI-Development/psych_llm_study
python3 -m venv .venv
```

### Step 3: Activate the virtual environment

**macOS/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

You should see `(.venv)` in your terminal prompt.

### Step 4: Install dependencies

```bash
pip install --upgrade pip
pip install -e .
```

This will install:
- The psych_llm_study package
- llm-client as an editable dependency (from ../llm-client)
- All required dependencies (requests, python-dotenv, etc.)

### Step 5: Verify installation

```bash
python -c "from llm_client import LLMClient; print('Success!')"
```

If you see "Success!", you're ready to go!

## Configuration

### 1. Set up your model registry

The project uses `probe_models.json` for model metadata. By default, it looks for:
```
/Users/toddfirsich/AI-Development/llm-model-update/probes/probe_models.json
```

**Option A: Use the default path**
- Clone or copy the `llm-model-update` repository to `~/AI-Development/`

**Option B: Use your own path**
- Edit `models.json` and update the `probe_models_path` field:
```json
{
  "models": [...],
  "probe_models_path": "/your/path/to/probe_models.json"
}
```

**Option C: Create a minimal probe_models.json**
Create your own at any location:
```json
{
  "models": [
    {
      "name": "qwen3:14b",
      "backend": "ollama",
      "enabled": true
    }
  ]
}
```

### 2. Configure API keys (for cloud models)

Create or edit `~/.env`:
```bash
# For Ollama Cloud models
OLLAMA_API_KEY=your-ollama-api-key

# For xAI/Grok models
XAI_API_KEY=your-xai-api-key
```

### 3. Configure your study

Edit `questions.json` to add your research questions.

Edit `models.json` to specify which models to test.

## Verification

Test your setup:

```bash
# Activate environment
source .venv/bin/activate

# Test a simple query
python -c "
from llm_client import LLMClient
client = LLMClient(
    models_file='/path/to/probe_models.json',
    model='qwen3:14b'
)
ok, msg = client.health_check()
print(f'Health check: {msg}')
"
```

## Troubleshooting

### "llm_client not found"

**Cause:** Virtual environment not activated or installation failed.

**Fix:**
```bash
source .venv/bin/activate
pip install -e .
```

### "Model not found in registry"

**Cause:** The model name in `models.json` doesn't exist in `probe_models.json`.

**Fix:** 
- Check model names match exactly
- Verify `probe_models_path` in `models.json` is correct
- Ensure `probe_models.json` contains the model

### "Backend unavailable"

**Cause:** API keys not set or local server not running.

**Fix for cloud models:**
```bash
# Check ~/.env has your API keys
cat ~/.env
```

**Fix for local models:**
```bash
# Start Ollama (if using ollama backend)
ollama serve

# Or start llama.cpp server (if using llamacpp backend)
llama-server --model /path/to/model.gguf
```

### "Import Error: No module named 'requests'"

**Cause:** Dependencies not installed correctly.

**Fix:**
```bash
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### Path issues on Windows

**Cause:** Path separators differ on Windows.

**Fix:** Edit `models.json` and use forward slashes or escaped backslashes:
```json
"probe_models_path": "C:/Users/YourName/AI-Development/probe_models.json"
```

## Updating

To update to the latest version:

```bash
cd ~/AI-Development/psych_llm_study
git pull

cd ~/AI-Development/llm-client
git pull

cd ~/AI-Development/psych_llm_study
source .venv/bin/activate
pip install -e . --upgrade
```

## Uninstallation

To remove the project:

```bash
# Deactivate virtual environment if active
deactivate

# Remove directories
rm -rf ~/AI-Development/psych_llm_study
rm -rf ~/AI-Development/llm-client  # if no longer needed
```

## Next Steps

See [QUICKSTART.md](QUICKSTART.md) for usage instructions.
