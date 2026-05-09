#!/bin/bash
# setup.sh - Automated setup for psych_llm_study project
#
# This script will:
# 1. Check if llm-client exists, clone if needed
# 2. Create a virtual environment
# 3. Install dependencies
# 4. Verify the setup

set -e  # Exit on error

echo "========================================================================"
echo "Psychology LLM Study - Setup"
echo "========================================================================"
echo ""

# Determine the absolute path to this script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"
PARENT_DIR="$(dirname "$PROJECT_ROOT")"
LLM_CLIENT_DIR="$PARENT_DIR/llm-client"

echo "Project directory: $PROJECT_ROOT"
echo "Looking for llm-client at: $LLM_CLIENT_DIR"
echo ""

# Step 1: Check for llm-client
echo "Step 1: Checking for llm-client..."
if [ -d "$LLM_CLIENT_DIR" ]; then
    echo "✓ Found llm-client at $LLM_CLIENT_DIR"
else
    echo "✗ llm-client not found"
    echo ""
    echo "Cloning llm-client from GitHub..."
    cd "$PARENT_DIR"
    git clone https://github.com/BoilerToad/llm-client.git
    echo "✓ llm-client cloned successfully"
fi
echo ""

# Step 2: Create virtual environment
echo "Step 2: Creating virtual environment..."
cd "$PROJECT_ROOT"
if [ -d ".venv" ]; then
    echo "✓ Virtual environment already exists"
else
    python3 -m venv .venv
    echo "✓ Virtual environment created"
fi
echo ""

# Step 3: Activate and install dependencies
echo "Step 3: Installing dependencies..."
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install the project in editable mode
pip install -e .

echo "✓ Dependencies installed"
echo ""

# Step 4: Verify setup
echo "Step 4: Verifying installation..."
python tests/verify_setup.py
