"""
test_reproducibility.py — Deterministic Reproducibility Verification
Demonstrates that executing dataset generation twice with fixed master seed 20261022
yields 100% bit-level matching row counts and cryptographic SHA-256 checksums across all tables.

Usage:
    python tests/test_reproducibility.py
    pytest tests/test_reproducibility.py
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from generator import generate_all, SEED
import run


def test_seed_20261022_deterministic_reproducibility():
    """
    Asserts bit-level reproducibility across two consecutive runs using seed 20261022.
    Row counts and SHA-256 table checksums must match across all 11+ entities.
    """
    scale = 1.0  # Full master baseline scale: 5,000 cust, 8,000 ord, 2,000 cmp, 6,000 msg
    print(f"\n[REPRODUCIBILITY TEST] Executing Run 1 with Seed {SEED} at scale {scale}x...")
    data1 = generate_all(scale=scale)
    hash1 = run.compute_dataset_hash(data1)

    print(f"[REPRODUCIBILITY TEST] Executing Run 2 with Seed {SEED} at scale {scale}x...")
    data2 = generate_all(scale=scale)
    hash2 = run.compute_dataset_hash(data2)

    # Table-by-table verification
    print("\n" + "=" * 72)
    print("  DETERMINISTIC REPRODUCIBILITY AUDIT REPORT (SEED: %d)" % SEED)
    print("=" * 72)
    print("  %-20s | %-12s | %-12s | %s" % ("Entity / Table", "Run 1 Count", "Run 2 Count", "Status"))
    print("  " + "-" * 68)

    all_matched = True
    for tbl in sorted(data1.keys()):
        records1 = data1[tbl] if isinstance(data1[tbl], list) else []
        records2 = data2[tbl] if isinstance(data2[tbl], list) else []
        count1 = len(records1)
        count2 = len(records2)
        h1 = run.compute_table_hash(records1)
        h2 = run.compute_table_hash(records2)

        match = (count1 == count2) and (h1 == h2)
        if not match:
            all_matched = False
        status_str = "MATCH (OK)" if match else "MISMATCH (FAIL)"
        print("  %-20s | %12d | %12d | %s" % (tbl, count1, count2, status_str))
        assert count1 == count2, f"Count mismatch in {tbl}: {count1} != {count2}"
        assert h1 == h2, f"Checksum mismatch in {tbl}: {h1} != {h2}"

    print("  " + "-" * 68)
    print(f"  Composite Run 1 Hash: {hash1}")
    print(f"  Composite Run 2 Hash: {hash2}")
    print(f"  Overall Reproducibility: {'100% BIT-LEVEL MATCH' if (hash1 == hash2) else 'FAILED'}")
    print("=" * 72 + "\n")

    assert hash1 == hash2, "Composite dataset SHA-256 mismatch between runs"
    assert all_matched, "Table-level checks did not all pass"


if __name__ == "__main__":
    try:
        test_seed_20261022_deterministic_reproducibility()
        print("[SUCCESS] Deterministic reproducibility verified: Seed 20261022 yields matching row counts & checksums across all tables.")
        sys.exit(0)
    except AssertionError as err:
        print(f"[FAIL] Reproducibility failure: {err}")
        sys.exit(1)

