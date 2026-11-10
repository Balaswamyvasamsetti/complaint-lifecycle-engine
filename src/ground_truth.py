# ground_truth.py — Exports labelled anomalies/edge cases separately
# Never leaks into input feature files

import csv
import json
import os

GT_FIELDS = ["complaint_id", "issue_type", "description"]


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

    print("[GROUND TRUTH] %d anomalies -> ground_truth.csv + ground_truth.json" % len(anomalies))
    return json_path, csv_path
