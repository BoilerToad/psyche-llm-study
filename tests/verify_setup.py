#!/usr/bin/env python3
"""
verify_setup.py
───────────────
Verify that the psych_llm_study environment is correctly set up.

Run this after installation to check:
- Python version
- llm_client import
- Configuration files
- Model registry (models.json)

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
    print(f"  ✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.13+)")
    return False


def check_llm_client():
    """Check if llm_client can be imported."""
    print("\nChecking llm_client package...")
    try:
        import llm_client  # pylint: disable=import-outside-toplevel,unused-import
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


def check_model_registry():
    """Check if models.json contains valid model entries."""
    print("\nChecking model registry...")

    try:
        with open("models.json", "r", encoding="utf-8") as f:
            registry = json.load(f)

        models = registry.get("models", [])
        if not models:
            print("  ✗ No models found in models.json")
            return False

        enabled_count = len([m for m in models if m.get("enabled", True)])
        print(f"  ✓ Contains {len(models)} model(s)")
        print(f"  ✓ {enabled_count} enabled model(s)")

        # Check for required fields in first model
        if models:
            first_model = models[0]
            required_fields = ["name", "backend"]
            missing = [f for f in required_fields if f not in first_model]
            if missing:
                print(f"  ⚠️  Model entries missing fields: {missing}")
                return False

        return True

    except FileNotFoundError:
        print("  ✗ models.json not found")
        return False
    except json.JSONDecodeError:
        print("  ✗ Invalid JSON in models.json")
        return False
    except Exception as e:  # pylint: disable=broad-exception-caught
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
        check_model_registry(),
        check_virtual_env(),
    ]

    print("\n" + "="*70)

    if all(checks):
        print("✓ All checks passed! Setup is complete.")
        print("="*70)
        print("\nNext steps:")
        print("  1. Edit questions.json with your research questions")
        print("  2. Edit models.json with your target models")
        print("  3. Create an experiment:")
        print("       python scripts/new_experiment.py --id <id> --name '<name>'")
        print("  4. Run: python scripts/run_study.py --experiment <id>")
        print("\nSee QUICKSTART.md for detailed usage instructions.")
        return 0
    print("✗ Some checks failed. Please fix the issues above.")
    print("="*70)
    print("\nFor help, see:")
    print("  - INSTALL.md for installation instructions")
    print("  - QUICKSTART.md for usage guide")
    print("  - README.md for project overview")
    return 1


if __name__ == "__main__":
    sys.exit(main())
