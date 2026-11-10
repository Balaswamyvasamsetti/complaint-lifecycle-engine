"""
run.py — Master Orchestrator for Complaint Lifecycle Engine
Executes full synthetic generation, multi-layer validation, multi-format export,
ground truth isolation, and reproducibility verification.

Usage:
    python src/run.py                          # Full baseline dataset (scale 1.0: 5k cust, 8k ord, 2k cmp, 6k msg)
    python src/run.py --scale 0.1              # Starter dataset (10% scale)
    python src/run.py --reproducibility-check  # Regenerates twice & verifies bit-level hash matching
    python src/run.py --seed-db --clean        # Cleans database and loads full dataset
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from generator import generate_all, SEED
from validator import validate, summarise
from exporter import export_all
from ground_truth import export_ground_truth
import db

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
CSV_DIR = os.path.join(BASE_DIR, "csv")
JSON_DIR = os.path.join(BASE_DIR, "json")
SQL_DIR = os.path.join(BASE_DIR, "sql")
GT_DIR = os.path.join(BASE_DIR, "ground_truth")


def compute_table_hash(records: list) -> str:
    """Computes SHA-256 hash for a single table."""
    hasher = hashlib.sha256()
    for r in records:
        if isinstance(r, dict):
            serialized = json.dumps(r, sort_keys=True, default=str)
            hasher.update(serialized.encode("utf-8"))
    return hasher.hexdigest()


def compute_dataset_hash(data: dict) -> str:
    """Computes a deterministic cryptographic hash across all tables and records."""
    hasher = hashlib.sha256()
    for tbl in sorted(data.keys()):
        records = data[tbl]
        if isinstance(records, list):
            hasher.update(tbl.encode("utf-8"))
            hasher.update(str(len(records)).encode("utf-8"))
            for r in records:
                if isinstance(r, dict):
                    serialized = json.dumps(r, sort_keys=True, default=str)
                    hasher.update(serialized.encode("utf-8"))
    return hasher.hexdigest()


def run(scale: float = 1.0, seed_database: bool = True, clean_first: bool = False):
    print("\n" + "=" * 65)
    print("  COMPLAINT LIFECYCLE ENGINE — PRODUCTION DATA PIPELINE")
    print("  Scale Factor: %.2fx | Master Seed: %d" % (scale, SEED))
    print("=" * 65 + "\n")

    # Step 1 & 2: Generation
    print("[PIPELINE 1/5] Generating synthetic master, transaction & event records...")
    data = generate_all(scale=scale)

    # Step 3: Validation
    print("\n[PIPELINE 2/5] Running multi-layer validation audit...")
    errors = validate(data)
    is_valid = summarise(errors, out_dir=BASE_DIR)

    # Step 4: Export CSV, JSON, and SQL
    print("\n[PIPELINE 3/5] Exporting CSV, JSON, and SQL seed/schema artifacts...")
    manifest = export_all(data, CSV_DIR, JSON_DIR, SQL_DIR)

    # Step 5: Export Ground Truth
    print("\n[PIPELINE 4/5] Isolating ground-truth anomaly repository...")
    gt_json, gt_csv = export_ground_truth(data["anomalies"], GT_DIR)

    # Step 6: Database Seeding
    if seed_database:
        print("\n[PIPELINE 5/5] Initialising and seeding persistence layer...")
        db.init_db()
        if clean_first:
            db.clean_database()
        db.bulk_load(data)

    dataset_hash = compute_dataset_hash(data)

    print("\n" + "=" * 65)
    print("  PIPELINE EXECUTION SUMMARY")
    print("=" * 65)
    for entry in manifest:
        print("  %-22s : %6d records" % (entry["table"], entry["row_count"]))
    print("  %-22s : %6d anomalies (isolated in ground truth)" % ("anomalies", len(data["anomalies"])))
    print("  %-22s : %s" % ("Validation Status", "PASSED (Zero Defect)" if is_valid else "DEFECTS DETECTED"))
    print("  %-22s : %s" % ("Dataset SHA-256", dataset_hash[:16] + "..." + dataset_hash[-16:]))
    print("=" * 65 + "\n")

    return data, dataset_hash


def verify_reproducibility(scale: float = 0.1):
    print("\n" + "=" * 70)
    print("  AUTOMATED SEED REPRODUCIBILITY VERIFICATION")
    print("  Master Seed: %d | Test Scale: %.2fx" % (SEED, scale))
    print("=" * 70)

    print("\n>>> Executing Run 1 with Seed %d..." % SEED)
    data1, hash1 = run(scale=scale, seed_database=False)

    print("\n>>> Executing Run 2 with Seed %d..." % SEED)
    data2, hash2 = run(scale=scale, seed_database=False)

    print("\n" + "-" * 70)
    print("  TABLE-BY-TABLE ROW COUNT & CHECKSUM COMPARISON:")
    print("  %-20s | %-12s | %-12s | %s" % ("Table", "Run 1 Count", "Run 2 Count", "Checksum Match"))
    print("  " + "-" * 66)

    table_report = {}
    all_matched = True

    for tbl in sorted(data1.keys()):
        count1 = len(data1[tbl]) if isinstance(data1[tbl], list) else 0
        count2 = len(data2[tbl]) if isinstance(data2[tbl], list) else 0
        tbl_hash1 = compute_table_hash(data1[tbl]) if isinstance(data1[tbl], list) else ""
        tbl_hash2 = compute_table_hash(data2[tbl]) if isinstance(data2[tbl], list) else ""
        match = (count1 == count2) and (tbl_hash1 == tbl_hash2)
        if not match:
            all_matched = False

        table_report[tbl] = {
            "run1_count": count1,
            "run2_count": count2,
            "counts_match": count1 == count2,
            "run1_hash": tbl_hash1,
            "run2_hash": tbl_hash2,
            "checksum_match": match
        }
        status_icon = "MATCH (OK)" if match else "MISMATCH (FAIL)"
        print("  %-20s | %12d | %12d | %s" % (tbl, count1, count2, status_icon))

    print("  " + "-" * 66)
    print("  Composite Run 1 SHA-256: %s" % hash1)
    print("  Composite Run 2 SHA-256: %s" % hash2)

    overall_match = (hash1 == hash2) and all_matched
    print("\n  Overall Status: %s" % ("VERIFIED (100% BIT-LEVEL MATCH)" if overall_match else "FAILED"))
    print("=" * 70 + "\n")

    # Export reproducibility report
    os.makedirs(BASE_DIR, exist_ok=True)
    report_path = os.path.join(BASE_DIR, "reproducibility_report.json")
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "scale": scale,
        "overall_status": "PASSED" if overall_match else "FAILED",
        "composite_sha256": hash1 if overall_match else None,
        "run1_sha256": hash1,
        "run2_sha256": hash2,
        "table_comparisons": table_report
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("  [AUDIT] Reproducibility verification evidence saved -> %s\n" % report_path)

    return overall_match


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Complaint Lifecycle Data Generator")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Volume scale (1.0 = 5k/8k/2k/6k baseline, 0.1 = starter)")
    parser.add_argument("--reproducibility-check", action="store_true",
                        help="Generate twice with fixed seed and compare row counts and checksums")
    parser.add_argument("--seed-db", action="store_true", default=True,
                        help="Seed the active database with generated records")
    parser.add_argument("--clean", action="store_true", default=False,
                        help="Clean existing database tables before loading")
    args = parser.parse_args()

    if args.reproducibility_check:
        success = verify_reproducibility(scale=args.scale)
        sys.exit(0 if success else 1)
    else:
        run(scale=args.scale, seed_database=args.seed_db, clean_first=args.clean)
