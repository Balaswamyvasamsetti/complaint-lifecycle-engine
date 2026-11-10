"""
Ground Truth — exports labelled anomalies/edge cases separately.
Never leaks into input feature files.
"""

import json
import csv
import os

GROUND_TRUTH_FIELDS = ["complaint_id", "issue_type", "description"]


def export_ground_truth(anomalies, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(out_dir, "ground_truth.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(anomalies, f, indent=2)

    # CSV
    csv_path = os.path.join(out_dir, "ground_truth.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GROUND_TRUTH_FIELDS)
        writer.writeheader()
        for row in anomalies:
            writer.writerow({k: row.get(k, "") for k in GROUND_TRUTH_FIELDS})

    print(f"[GROUND TRUTH] {len(anomalies)} anomalies -> {json_path}, {csv_path}")
    return json_path, csv_path
