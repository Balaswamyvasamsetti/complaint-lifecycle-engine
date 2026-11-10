"""
run.py -- Orchestrator
Usage:
    python run.py                  # full scale (5000/8000/2000/6000)
    python run.py --scale 0.1      # starter dataset (10%)
    python run.py --reproducibility-check  # generate twice, compare checksums
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from generator    import generate_all
from validator    import validate, summarise
from exporter     import export_all
from ground_truth import export_ground_truth

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
CSV_DIR  = os.path.join(BASE_DIR, "csv")
JSON_DIR = os.path.join(BASE_DIR, "json")
GT_DIR   = os.path.join(BASE_DIR, "ground_truth")


def checksum(data):
    summary = {k: len(v) for k, v in data.items() if isinstance(v, list)}
    return hashlib.md5(json.dumps(summary, sort_keys=True).encode()).hexdigest(), summary


def run(scale=1.0):
    print("\n" + "=" * 60)
    print("  Complaint Management System - Data Generator")
    print("  Scale: %.2fx | Seed: 20261022" % scale)
    print("=" * 60 + "\n")

    print("[STEP 1] Generating synthetic data...")
    data = generate_all(scale=scale)

    print("\n[STEP 2] Validating data...")
    errors = validate(data)
    passed = summarise(errors)

    print("\n[STEP 3] Exporting CSV / JSON...")
    manifest = export_all(data, CSV_DIR, JSON_DIR)

    print("\n[STEP 4] Exporting ground truth...")
    export_ground_truth(data["anomalies"], GT_DIR)

    if errors:
        err_path = os.path.join(BASE_DIR, "validation_errors.json")
        with open(err_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, indent=2)
        print("\n[STEP 5] Validation errors saved -> %s" % err_path)
    else:
        print("\n[STEP 5] All validation checks passed - OK")

    print("\n" + "=" * 60)
    print("  GENERATION SUMMARY")
    print("=" * 60)
    for entry in manifest:
        print("  %-20s %6d rows" % (entry["table"], entry["row_count"]))
    print("  %-20s %6d labelled edge cases" % ("anomalies", len(data["anomalies"])))
    print("=" * 60 + "\n")

    cs, counts = checksum(data)
    print("  Checksum (row counts): %s" % cs)
    return data, cs


def reproducibility_check():
    print("\n[REPRODUCIBILITY] Run 1...")
    _, cs1 = run(scale=0.1)
    print("\n[REPRODUCIBILITY] Run 2...")
    _, cs2 = run(scale=0.1)
    if cs1 == cs2:
        print("\n[OK] REPRODUCIBLE - both runs match: %s" % cs1)
    else:
        print("\n[FAIL] MISMATCH - Run1=%s, Run2=%s" % (cs1, cs2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Complaint Management Data Generator")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Scale factor (1.0 = full, 0.1 = starter)")
    parser.add_argument("--reproducibility-check", action="store_true",
                        help="Generate twice and compare checksums")
    args = parser.parse_args()

    if args.reproducibility_check:
        reproducibility_check()
    else:
        run(scale=args.scale)
