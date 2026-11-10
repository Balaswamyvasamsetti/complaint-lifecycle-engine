# test_system.py — Comprehensive end-to-end test suite for Complaint Lifecycle Engine

import os
import sys
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import schema
import generator
import validator
import exporter
import ground_truth
import db
import ai_engine
from api import app


@pytest.fixture(scope="session")
def sample_dataset():
    """Generates a small starter dataset (scale 0.05) for testing."""
    return generator.generate_all(scale=0.05)


def test_schema_integrity():
    """Verify master configuration data contains required items."""
    assert len(schema.CATEGORIES) == 10
    assert len(schema.PRIORITY_RULES) == 4
    assert len(schema.PRODUCTS) >= 10
    assert "CRITICAL" in schema.TEAMS
    assert "Safety-Response" in schema.TEAMS["CRITICAL"]


def test_deterministic_id_conventions(sample_dataset):
    """Verify deterministic zero-padded ID naming conventions across entities."""
    for c in sample_dataset["customers"]:
        assert c["customer_id"].startswith("CUS-")
        assert len(c["customer_id"]) == 10  # CUS-000001

    for o in sample_dataset["orders"]:
        assert o["order_id"].startswith("ORD-2026-")

    for cmp in sample_dataset["complaints"]:
        assert cmp["complaint_id"].startswith("CMP-2026-")
        assert len(cmp["complaint_id"]) == 15  # CMP-2026-000001

    for a in sample_dataset["assignments"]:
        assert a["assignment_id"].startswith("ASN-")
        assert len(a["assignment_id"]) == 10  # ASN-000001

    for s in sample_dataset["sla_clocks"]:
        assert s["sla_id"].startswith("SLA-")

    for r in sample_dataset["resolutions"]:
        assert r["resolution_id"].startswith("RES-")

    for sv in sample_dataset["surveys"]:
        assert sv["survey_id"].startswith("SRV-")


def test_priority_rule_engine():
    """Verify priority rule engine evaluates priority strictly per specification."""
    # 1. Critical cases: Safety OR Vulnerable OR Fraud
    assert generator.priority_from_rules(True, False, "Neutral", 50, 1, False) == "CRITICAL"
    assert generator.priority_from_rules(False, True, "Neutral", 50, 1, False) == "CRITICAL"
    assert generator.priority_from_rules(False, False, "Positive", 50, 1, True) == "CRITICAL"

    # 2. High cases: (Negative AND order_value > 500) OR recurrence >= 3
    assert generator.priority_from_rules(False, False, "Negative", 600, 1, False) == "HIGH"
    assert generator.priority_from_rules(False, False, "Neutral", 50, 3, False) == "HIGH"

    # 3. Medium cases: Negative OR (100 <= order_value <= 500)
    assert generator.priority_from_rules(False, False, "Negative", 50, 1, False) == "MEDIUM"
    assert generator.priority_from_rules(False, False, "Neutral", 250, 1, False) == "MEDIUM"

    # 4. Low cases: Neutral/Positive AND order_value < 100
    assert generator.priority_from_rules(False, False, "Neutral", 40, 1, False) == "LOW"
    assert generator.priority_from_rules(False, False, "Positive", 90, 1, False) == "LOW"


def test_sla_calculation():
    """Verify base SLA hours and priority multipliers produce exact deadlines."""
    # CAT-04 (Product Safety base = 4h) with CRITICAL (0.25x) -> 1h
    assert generator._sla_hours_for("CAT-04", "CRITICAL") == 1.0
    # CAT-01 (Billing base = 48h) with MEDIUM (1.0x) -> 48h
    assert generator._sla_hours_for("CAT-01", "MEDIUM") == 48.0
    # CAT-01 (Billing base = 48h) with LOW (1.5x) -> 72h
    assert generator._sla_hours_for("CAT-01", "LOW") == 72.0


def test_validation_engine(sample_dataset):
    """Verify validation engine passes genuine records with zero defects."""
    errors = validator.validate(sample_dataset)
    genuine_issues = [e for e in errors if not e.get("is_expected_anomaly")]
    assert len(genuine_issues) == 0, "Expected 0 genuine defects, found: %s" % genuine_issues

    expected_anomalies = [e for e in errors if e.get("is_expected_anomaly")]
    assert len(expected_anomalies) >= 4, "Expected edge cases were not properly caught"


def test_ground_truth_isolation(sample_dataset, tmp_path):
    """Verify ground truth edge cases are isolated and stripped from feature exports."""
    csv_dir = str(tmp_path / "csv")
    json_dir = str(tmp_path / "json")
    sql_dir = str(tmp_path / "sql")
    gt_dir = str(tmp_path / "ground_truth")

    exporter.export_all(sample_dataset, csv_dir, json_dir, sql_dir)
    gt_json, gt_csv = ground_truth.export_ground_truth(sample_dataset["anomalies"], gt_dir)

    assert os.path.exists(gt_json)
    assert os.path.exists(gt_csv)

    # Check exported CSV does not contain issue_type header
    with open(os.path.join(csv_dir, "complaints.csv"), "r", encoding="utf-8") as f:
        header = f.readline()
        assert "issue_type" not in header


def test_reproducibility():
    """Verify identical seeds produce 100% bit-level matching data across runs."""
    import run
    data1 = generator.generate_all(scale=0.02)
    hash1 = run.compute_dataset_hash(data1)

    data2 = generator.generate_all(scale=0.02)
    hash2 = run.compute_dataset_hash(data2)

    assert hash1 == hash2, "Non-deterministic generation output between repeated runs"


def test_database_persistence_and_event_sourcing(sample_dataset):
    """Verify database DDL, bulk loading, updates, and event logging."""
    db.init_db()
    db.bulk_load(sample_dataset)

    first_cmp = sample_dataset["complaints"][0]
    cmp_id = first_cmp["complaint_id"]

    fetched = db.get_complaint(cmp_id)
    assert fetched is not None
    assert fetched["complaint_id"] == cmp_id

    # Test status transition and event sourcing
    db.update_complaint_status(cmp_id, "In Progress", actor="Operations Analyst")
    updated = db.get_complaint(cmp_id)
    assert updated["status"] == "In Progress"

    # Check immutable events log
    events = db.get_complaint_events(cmp_id)
    assert len(events) >= 1
    assert any(e["event_type"] == "STATUS_CHANGED" for e in events)


def test_fastapi_rest_endpoints():
    """Verify REST API endpoints using FastAPI TestClient."""
    client = TestClient(app)

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Submit new complaint
    payload = {
        "channel": "Web",
        "complaint_text": "The power bank battery overheated and melted during charging.",
        "order_value": 59.99,
        "is_safety_issue": True,
        "is_vulnerable": False,
        "recurrence_count": 1
    }
    res = client.post("/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "complaint_id" in data
    assert data["priority"] == "CRITICAL"
    assert data["assigned_team"] in schema.TEAMS["CRITICAL"]
    cmp_id = data["complaint_id"]

    # 3. Retrieve complaint details
    res = client.get("/complaints/%s" % cmp_id)
    assert res.status_code == 200
    detail = res.json()
    assert detail["complaint"]["complaint_id"] == cmp_id
    assert detail["current_assignment"] is not None

    # 4. Check SLA endpoint
    res = client.get("/complaints/%s/sla" % cmp_id)
    assert res.status_code == 200
    sla_data = res.json()
    assert "hours_remaining" in sla_data

    # 5. Resolve complaint
    res_payload = {
        "resolution_type": "Refund",
        "resolved_by": "AGT-SR-01",
        "notes": "Full replacement issued with apology credit",
        "refund_amount": 59.99
    }
    res = client.post("/complaints/%s/resolve" % cmp_id, json=res_payload)
    assert res.status_code == 201
    assert res.json()["resolution_type"] == "Refund"

    # 6. Submit survey
    survey_payload = {
        "rating": 5,
        "feedback_text": "Resolved very swiftly!",
        "nps_score": 10
    }
    res = client.post("/complaints/%s/survey" % cmp_id, json=survey_payload)
    assert res.status_code == 201

    # 7. Check audit events timeline
    res = client.get("/complaints/%s/events" % cmp_id)
    assert res.status_code == 200
    events = res.json()["timeline"]
    assert len(events) >= 3  # CREATED, RESOLVED, SURVEY

    # 8. Check analytics summary
    res = client.get("/analytics/summary")
    assert res.status_code == 200
    analytics = res.json()
    assert "total_complaints" in analytics

    # 9. Check Executive Control Plane UI Dashboard
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "Complaint Lifecycle Engine" in res.text

