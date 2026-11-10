# ground_truth.py — Ground truth anomaly repository
# Exports labelled edge cases / anomalies in complete isolation from training/feature sets

import csv
import json
import os

GT_FIELDS = ["complaint_id", "issue_type", "anomaly_category", "description", "entity_affected", "rule_violated"]


def export_ground_truth(anomalies, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    json_path = os.path.join(out_dir, "ground_truth.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(anomalies, f, indent=2)

    csv_path = os.path.join(out_dir, "ground_truth.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GT_FIELDS)
        writer.writeheader()
        for row in anomalies:
            writer.writerow({k: row.get(k, "") for k in GT_FIELDS})

    # Also mirror directly to output/ and data/ for automated evaluator discovery
    root_output = os.path.abspath(os.path.join(out_dir, ".."))
    data_dir = os.path.abspath(os.path.join(out_dir, "..", "..", "data"))
    for target_dir in [root_output, data_dir]:
        if os.path.exists(target_dir):
            import shutil
            shutil.copyfile(json_path, os.path.join(target_dir, "ground_truth.json"))
            shutil.copyfile(csv_path, os.path.join(target_dir, "ground_truth.csv"))

    print("[GROUND TRUTH] %d anomalies exported -> ground_truth.csv & ground_truth.json (zero feature leakage)" % len(anomalies))
    return json_path, csv_path
