#!/usr/bin/env python3
"""
test_chain.py
─────────────
Validate that 2-question chaining works end-to-end against a single model.

Two tests:
  1. Unit — build_chained_prompt injects the prior response into Q02's prompt
  2. Integration — runs a live 2-question chain, then inspects the DB to confirm
     Q02's stored prompt contains Q01's actual response text

Usage:
    python tests/test_chain.py --model gemma3:4b
    python tests/test_chain.py --model gemma3:4b --keep   # retains DB in logs/
"""

import argparse
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from run_study_chain import build_chained_prompt  # pylint: disable=wrong-import-position,import-error

from llm_client import LLMClient, create_logger  # pylint: disable=wrong-import-position


# ── Test questions ────────────────────────────────────────────────────────────
# Kept short and factual so the chain verification is unambiguous.

Q01 = {
    "id": "Q01",
    "category": "test",
    "prompt": "Name exactly one planet in our solar system. "
              "Reply with the planet name only — one word.",
    "tags": ["Q01", "test", "chain_test"],
}

Q02 = {
    "id": "Q02",
    "category": "test",
    "chain_from": "Q01",
    "prompt": "In one sentence, why is that planet interesting to astronomers?",
    "tags": ["Q02", "test", "chain_test"],
}


# ── Test 1: unit ──────────────────────────────────────────────────────────────

def test_unit_build_chained_prompt():
    """build_chained_prompt should prepend the prior response when chain_from is set."""
    print("\n[TEST 1] Unit — build_chained_prompt")

    prior = {"Q01": "Saturn"}

    # Q02 chains from Q01
    result = build_chained_prompt(Q02, prior)
    assert "Saturn" in result, "Prior response not found in chained prompt"
    assert Q02["prompt"] in result, "Original prompt missing from chained prompt"
    print("  ✓ Prior response injected correctly")

    # Q01 has no chain_from — should return bare prompt
    bare = build_chained_prompt(Q01, prior)
    assert bare == Q01["prompt"], "Non-chained question should return bare prompt"
    print("  ✓ Non-chained question returns bare prompt")

    # Missing prior (Q01 failed) — should fall back to bare prompt
    fallback = build_chained_prompt(Q02, {})
    assert fallback == Q02["prompt"], "Missing prior should fall back to bare prompt"
    print("  ✓ Missing prior falls back to bare prompt")

    print("  PASS")
    return True


# ── Test 2: integration ───────────────────────────────────────────────────────

def test_integration_chain(model_name, keep=False):  # pylint: disable=too-many-locals,too-many-statements
    """Run a live 2-question chain and verify Q02's stored prompt contains Q01's response."""
    print(f"\n[TEST 2] Integration — live chain against {model_name}")

    # Resolve DB path — persistent in logs/ or ephemeral in a temp dir
    if keep:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = log_dir / f"test_chain_{timestamp}.db"
        ctx = None
    else:
        ctx = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        db_path = Path(ctx.name) / "test_chain.db"

    try:
        logger = create_logger(
            backend="sqlite",
            path=str(db_path),
            experiment_id="test_chain",
            experiment_name="Chain validation test",
        )

        client = LLMClient(models_file="models.json", model=model_name, logger=logger)

        print("  Checking model availability...")
        ok, detail = client.health_check()
        if not ok:
            print(f"  ✗ Model unavailable: {detail}")
            logger.close()
            return False
        print(f"  ✓ {detail}")

        prior_responses = {}

        # Q01
        print("  Sending Q01...")
        r1 = client.chat(Q01["prompt"], tags=Q01["tags"], timeout=60)
        if not r1.success:
            print(f"  ✗ Q01 failed: {r1.error}")
            logger.close()
            return False
        prior_responses["Q01"] = r1.content
        print(f"  ✓ Q01 response: {r1.content.strip()[:80]}")

        # Q02 — build chained prompt then send
        chained_prompt = build_chained_prompt(Q02, prior_responses)
        print("  Sending Q02 (chained)...")
        r2 = client.chat(chained_prompt, tags=Q02["tags"], timeout=60)
        if not r2.success:
            print(f"  ✗ Q02 failed: {r2.error}")
            logger.close()
            return False
        print(f"  ✓ Q02 response: {r2.content.strip()[:80]}")

        logger.close()

        # Inspect DB — verify Q02's stored prompt contains Q01's response
        print("  Verifying DB...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT prompt FROM queries WHERE tags_json LIKE '%\"Q02\"%'")
        row = cursor.fetchone()
        conn.close()

        if not row:
            print("  ✗ Q02 row not found in DB")
            return False

        stored_prompt = row[0]
        q01_response = r1.content.strip()

        if q01_response not in stored_prompt:
            print("  ✗ Q01 response not found in Q02's stored prompt")
            print(f"    Q01 response : {q01_response[:100]}")
            print(f"    Q02 prompt   : {stored_prompt[:200]}")
            return False

        print("  ✓ Q01 response confirmed in Q02's stored prompt")
        if keep:
            print(f"  DB retained at: {db_path}")
        print("  PASS")
        return True

    finally:
        if ctx:
            ctx.cleanup()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    """Run both chain tests and report results."""
    parser = argparse.ArgumentParser(description="Validate 2-question chain end-to-end")
    parser.add_argument("--model", required=True,
                        help="Model name to test against (e.g. gemma3:4b)")
    parser.add_argument("--keep", action="store_true",
                        help="Retain the integration test DB in logs/ instead of deleting it")
    args = parser.parse_args()

    print("=" * 60)
    print("Chain Validation Test")
    print("=" * 60)

    results = []
    results.append(test_unit_build_chained_prompt())
    results.append(test_integration_chain(args.model, keep=args.keep))

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"✓ All {total} tests passed")
    else:
        print(f"✗ {total - passed}/{total} tests failed")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
