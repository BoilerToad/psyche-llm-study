#!/usr/bin/env python3
"""
verify_setup.py
───────────────
Verify that the psych_llm_study environment is correctly set up.

Run this after installation to check:
- Python version
- llm_client import
- Configuration files
- probe_models.json path

Usage:
    python verify_setup.py
"""

import json
import sys
from pathlib import Path


def check_python_version():
    """Check Python version meets requirements."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 13:
        print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.13+)")
        return False


def check_llm_client():
    """Check if llm_client can be imported."""
    print("\nChecking llm_client package...")
    try:
        from llm_client import LLMClient, create_logger
        print("  ✓ llm_client imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Failed to import llm_client: {e}")
        print("  Run: pip install -e .")
        return False


def check_config_files():
    """Check if configuration files exist."""
    print("\nChecking configuration files...")
    
    all_ok = True
    
    files = {
        "questions.json": "Questions configuration",
        "models.json": "Models configuration",
        "pyproject.toml": "Project configuration",
    }
    
    for filename, description in files.items():
        path = Path(filename)
        if path.exists():
            print(f"  ✓ {filename} ({description})")
        else:
            print(f"  ✗ {filename} missing ({description})")
            all_ok = False
    
    return all_ok


def check_probe_models():
    """Check if probe_models.json path is valid."""
    print("\nChecking probe_models.json...")
    
    try:
        with open("models.json", "r") as f:
            config = json.load(f)
        
        probe_path = config.get("probe_models_path")
        if not probe_path:
            print("  ⚠️  No probe_models_path specified in models.json")
            print("  You'll need to set this before running studies")
            return False
        
        probe_file = Path(probe_path)
        if probe_file.exists():
            print(f"  ✓ Found at: {probe_path}")
            
            # Check if it's valid JSON
            try:
                with open(probe_file, "r") as f:
                    data = json.load(f)
                models_count = len(data.get("models", []))
                print(f"  ✓ Contains {models_count} model(s)")
                return True
            except json.JSONDecodeError:
                print(f"  ✗ Invalid JSON in {probe_path}")
                return False
        else:
            print(f"  ✗ Not found at: {probe_path}")
            print("  Update probe_models_path in models.json")
            return False
            
    except Exception as e:
        print(f"  ✗ Error reading models.json: {e}")
        return False


def check_virtual_env():
    """Check if running in a virtual environment."""
    print("\nChecking virtual environment...")
    
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        print(f"  ✓ Running in virtual environment: {sys.prefix}")
        return True
    else:
        print("  ⚠️  Not running in a virtual environment")
        print("  Recommended: source .venv/bin/activate")
        return False


def main():
    """Run all verification checks."""
    print("="*70)
    print("Psychology LLM Study - Setup Verification")
    print("="*70)
    print()
    
    checks = [
        check_python_version(),
        check_llm_client(),
        check_config_files(),
        check_probe_models(),
        check_virtual_env(),
    ]
    
    print("\n" + "="*70)
    
    if all(checks):
        print("✓ All checks passed! Setup is complete.")
        print("="*70)
        print("\nNext steps:")
        print("  1. Edit questions.json with your research questions")
        print("  2. Edit models.json with your target models")
        print("  3. Run: python run_study.py")
        print("\nSee QUICKSTART.md for detailed usage instructions.")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print("="*70)
        print("\nFor help, see:")
        print("  - INSTALL.md for installation instructions")
        print("  - QUICKSTART.md for usage guide")
        print("  - README.md for project overview")
        return 1


if __name__ == "__main__":
    sys.exit(main())
