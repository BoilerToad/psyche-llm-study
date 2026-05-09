#!/usr/bin/env python3
"""
test_models.py
──────────────
Test connectivity to ALL models in models.json and provide
a comprehensive summary of model availability and metadata.

This tests every enabled model in the registry (30+ models).

Usage:
    python tests/test_models.py                    # test all enabled models
    python tests/test_models.py --backend ollama   # test only local ollama models
    python tests/test_models.py --backend xai      # test only xAI models
    python tests/test_models.py --family llama     # test only llama family models
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from llm_client import LLMClient


def load_models_registry(path: str = "models.json") -> dict:
    """Load the full models registry."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_model_metadata(model_name: str, registry: dict) -> dict:
    """Extract metadata for a model from registry."""
    models_list = registry.get("models", [])
    for model in models_list:
        if model.get("name") == model_name:
            return model
    return {}


def test_model_connectivity(model_name: str, models_file: str, log_file) -> dict:
    """Test if a model is accessible and responsive."""
    result = {
        "name": model_name,
        "available": False,
        "backend": None,
        "health_detail": None,
        "response_time": None,
        "test_query_success": False,
        "error": None,
        "raw_response": None,
    }

    # Log header
    log_file.write(f"\n{'='*80}\n")
    log_file.write(f"Model: {model_name}\n")
    log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
    log_file.write(f"{'='*80}\n")

    try:
        # Create client
        client = LLMClient(
            models_file=models_file,
            model=model_name,
        )

        result["backend"] = client.backend
        log_file.write(f"Backend: {client.backend}\n\n")

        # Test health check
        start = time.time()
        ok, detail = client.health_check()
        elapsed = time.time() - start

        result["health_detail"] = detail
        result["response_time"] = round(elapsed, 3)
        result["available"] = ok

        log_file.write(f"Health Check Result: {ok}\n")
        log_file.write(f"Health Check Detail: {detail}\n")
        log_file.write(f"Response Time: {elapsed:.3f}s\n\n")

        if not ok:
            result["error"] = detail
            log_file.write(f"ERROR: {detail}\n")
            log_file.flush()
            return result

        # Try a simple test query
        try:
            log_file.write("Test Query: 'What is 2+2?'\n")
            test_result = client.chat("What is 2+2?", timeout=240)
            result["test_query_success"] = test_result.success

            log_file.write(f"Query Success: {test_result.success}\n")
            if test_result.content:
                log_file.write(f"Response Content: {test_result.content[:200]}...\n")
            if test_result.raw:
                log_file.write(f"\\nRAW API RESPONSE:\\n{json.dumps(test_result.raw, indent=2)}\\n")
                result["raw_response"] = test_result.raw

            if not test_result.success:
                result["error"] = test_result.error
                log_file.write(f"Query Error: {test_result.error}\n")
        except Exception as e:  # pylint: disable=broad-exception-caught
            result["error"] = f"Query failed: {str(e)}"
            log_file.write(f"Query Exception: {str(e)}\n")

    except Exception as e:  # pylint: disable=broad-exception-caught
        result["error"] = str(e)
        log_file.write(f"\nCONNECTION ERROR: {str(e)}\n")

    log_file.flush()
    return result


def print_summary(results: list, registry: dict):  # pylint: disable=too-many-branches,too-many-statements
    """Print comprehensive summary of test results."""

    print("\n" + "="*80)
    print("MODEL CONNECTIVITY TEST SUMMARY")
    print("="*80)

    available = [r for r in results if r["available"]]
    unavailable = [r for r in results if not r["available"]]
    query_success = [r for r in results if r["test_query_success"]]

    print(f"\nTotal models tested: {len(results)}")
    print(f"✓ Available: {len(available)}")
    print(f"✓ Query success: {len(query_success)}")
    print(f"✗ Unavailable: {len(unavailable)}")

    # Detailed results
    print("\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80)

    for result in results:
        model_name = result["name"]
        metadata = get_model_metadata(model_name, registry)

        print(f"\n{model_name}")
        print("-" * len(model_name))

        # Status
        if result["available"]:
            status = "✓ AVAILABLE"
            if result["test_query_success"]:
                status += " & RESPONSIVE"
        else:
            status = "✗ UNAVAILABLE"
        print(f"Status: {status}")

        # Backend
        if result["backend"]:
            print(f"Backend: {result['backend']}")
        elif metadata.get("backend"):
            print(f"Backend: {metadata.get('backend')} (from registry)")

        # Response time
        if result["response_time"]:
            print(f"Health check: {result['response_time']}s")

        # Metadata from probe_models.json
        if metadata:
            if metadata.get("family"):
                print(f"Family: {metadata['family']}")
            if metadata.get("size_gb"):
                print(f"Size: {metadata['size_gb']} GB")
            if metadata.get("think_blocks"):
                print(f"Think blocks: {metadata['think_blocks']}")
            if metadata.get("geopolitical_origin"):
                print(f"Origin: {metadata['geopolitical_origin']}")

        # Health detail
        if result["health_detail"]:
            print(f"Detail: {result['health_detail']}")

        # Error
        if result["error"]:
            print(f"Error: {result['error']}")

    # Backend summary
    print("\n" + "="*80)
    print("BACKEND SUMMARY")
    print("="*80)

    backends = {}
    for result in results:
        backend = result["backend"] or "unknown"
        if backend not in backends:
            backends[backend] = {"total": 0, "available": 0, "responsive": 0}
        backends[backend]["total"] += 1
        if result["available"]:
            backends[backend]["available"] += 1
        if result["test_query_success"]:
            backends[backend]["responsive"] += 1

    for backend, stats in backends.items():
        print(f"\n{backend}:")
        print(f"  Total: {stats['total']}")
        print(f"  Available: {stats['available']}/{stats['total']}")
        print(f"  Responsive: {stats['responsive']}/{stats['total']}")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    if len(query_success) == len(results):
        print("\n✓ All models are available and responsive!")
        print("  You're ready to run: python scripts/run_study.py")
    elif len(available) == len(results):
        print("\n⚠️  All models are available but some queries failed.")
        print("  This may be due to rate limits or temporary issues.")
        print("  Try running the study - most issues resolve during actual runs.")
    else:
        print(f"\n⚠️  {len(unavailable)} model(s) unavailable.")
        print("\nFor unavailable models:")
        for result in unavailable:
            print(f"  - {result['name']}: {result['error']}")
        print("\nTroubleshooting:")
        print("  1. Check API keys in ~/.env (OLLAMA_API_KEY, XAI_API_KEY)")
        print("  2. Ensure local servers are running (ollama serve, llama-server)")
        print("  3. Verify model names match probe_models.json")
        print("  4. Check network connectivity for cloud models")

    print("\n" + "="*80)


def main():  # pylint: disable=too-many-locals
    """Run model connectivity tests."""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Test LLM model connectivity with optional filtering"
    )
    parser.add_argument(
        "--backend",
        choices=["ollama", "ollama_cloud", "llamacpp", "xai", "openai"],
        help="Filter models by backend type"
    )
    parser.add_argument(
        "--family",
        help="Filter models by family (e.g., llama, grok, gemma, mistral)"
    )
    args = parser.parse_args()

    print("="*80)
    print("Psychology LLM Study - Model Connectivity Test")
    print("="*80)

    # Load the full models registry
    print("\nLoading model registry...")
    models_file = "models.json"
    registry = load_models_registry(models_file)

    # Extract all enabled models
    all_models = registry.get("models", [])
    enabled_models = [m for m in all_models if m.get("enabled", True)]

    # Apply filters
    if args.backend:
        enabled_models = [m for m in enabled_models if m.get("backend") == args.backend]
        print(f"\nFiltering by backend: {args.backend}")

    if args.family:
        enabled_models = [m for m in enabled_models if m.get("family") == args.family]
        print(f"Filtering by family: {args.family}")

    # Extract just the names
    model_names = [m["name"] for m in enabled_models]

    if not model_names:
        print("❌ Error: No models match the filter criteria")
        return 1

    print(f"Total models in registry: {len(all_models)}")
    print(f"Enabled models to test: {len(model_names)}")
    print(f"Registry: {models_file}")

    # Create log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"model_test_{timestamp}.log"

    print(f"\n📝 Logging raw responses to: {log_path}")

    # Test each enabled model
    print("\nTesting models...")
    print("-" * 80)

    results = []
    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write("Model Connectivity Test\n")
        log_file.write(f"Started: {datetime.now().isoformat()}\n")
        log_file.write(f"Testing {len(model_names)} models\n")

        for i, model_name in enumerate(model_names, 1):
            print(f"\n[{i}/{len(model_names)}] Testing {model_name}...")
            result = test_model_connectivity(model_name, models_file, log_file)
            results.append(result)

            if result["available"]:
                status = "✓" if result["test_query_success"] else "⚠️"
                print(f"  {status} {result['health_detail']}")
            else:
                print(f"  ✗ {result['error']}")

    print(f"\n📝 Full test log saved to: {log_path}")

    # Print summary
    print_summary(results, registry)

    # Exit code
    all_available = all(r["available"] for r in results)
    return 0 if all_available else 1


if __name__ == "__main__":
    sys.exit(main())
