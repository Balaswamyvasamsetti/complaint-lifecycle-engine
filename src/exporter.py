"""
Exporter — writes all entity tables to CSV and JSON.
Strips issue_type/ground_truth fields from input feature files.
"""

import csv
import json
import os

# Fields to strip from input feature exports (ground truth only)
GT_FIELDS = {"issue_type"}


def _clean(records):
    """Remove ground-truth fields from records before export."""
    cleaned = []
    for r in records:
        cleaned.append({k: v for k, v in r.items() if k not in GT_FIELDS})
    return cleaned


def _write_csv(records, path, fieldnames=None):
    if not records:
        return
    if fieldnames is None:
        fieldnames = list(records[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def _write_json(records, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)


def export_all(data, csv_dir, json_dir):
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    tables = {
        "customers":      data["customers"],
        "products":       data["products"],
        "orders":         data["orders"],
        "categories":     data["categories"],
        "priority_rules": data["priority_rules"],
        "complaints":     data["complaints"],
        "assignments":    data["assignments"],
        "sla_clocks":     data["sla_clocks"],
        "messages":       data["messages"],
        "resolutions":    data["resolutions"],
        "surveys":        data["surveys"],
    }

    manifest = []
    for name, records in tables.items():
        cleaned = _clean(records)
        csv_path  = os.path.join(csv_dir,  f"{name}.csv")
        json_path = os.path.join(json_dir, f"{name}.json")
        _write_csv(cleaned, csv_path)
        _write_json(cleaned, json_path)
        manifest.append({
            "table":      name,
            "row_count":  len(cleaned),
            "csv":        csv_path,
            "json":       json_path,
        })
        print(f"  [EXPORT] {name}: {len(cleaned)} rows")

    # write manifest
    manifest_path = os.path.join(csv_dir, "..", "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest
