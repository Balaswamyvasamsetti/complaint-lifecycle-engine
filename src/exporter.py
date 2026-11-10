# exporter.py — Writes all entity tables to CSV and JSON
# Strips issue_type (ground-truth) fields from all input feature exports

import csv
import json
import os

GT_FIELDS = {"issue_type"}

TABLES = [
    "customers", "products", "orders", "categories",
    "priority_rules", "complaints", "assignments",
    "sla_clocks", "messages", "resolutions", "surveys",
]


def _clean(records):
    return [{k: v for k, v in r.items() if k not in GT_FIELDS} for r in records]


def _write_csv(records, path):
    if not records:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def _write_json(records, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)


def export_all(data, csv_dir, json_dir):
    os.makedirs(csv_dir,  exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    manifest = []
    for name in TABLES:
        records   = _clean(data[name])
        csv_path  = os.path.join(csv_dir,  name + ".csv")
        json_path = os.path.join(json_dir, name + ".json")
        _write_csv(records,  csv_path)
        _write_json(records, json_path)
        manifest.append({"table": name, "row_count": len(records), "csv": csv_path, "json": json_path})
        print("  [EXPORT] %-20s %d rows" % (name, len(records)))

    manifest_path = os.path.join(csv_dir, "..", "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest
