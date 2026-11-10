# db.py — Dual-Engine Persistence Layer (PostgreSQL / Neon + SQLite)
# Seamlessly routes queries to Neon/PostgreSQL when DATABASE_URL is configured,
# or to SQLite for standalone local execution. Preserves immutable event history.

import os
import sqlite3
import json
import uuid
import time
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

_sequence_lock = threading.RLock()

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "complaints.db")
DB_PATH = os.getenv("DB_PATH", DEFAULT_SQLITE_PATH)

_USE_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")))

if _USE_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        _USE_POSTGRES = False


def is_postgres() -> bool:
    return _USE_POSTGRES


_pg_conn = None


class _PooledPostgresWrapper:
    """Wraps psycopg2 connection so conn.close() keeps connection alive for reuse."""
    def __init__(self, real_conn):
        self._conn = real_conn

    def close(self):
        try:
            if not self._conn.closed:
                self._conn.commit()
        except Exception:
            pass

    def __getattr__(self, item):
        return getattr(self._conn, item)


def get_conn():
    global _pg_conn
    if _USE_POSTGRES:
        try:
            if _pg_conn is None or _pg_conn.closed != 0:
                _pg_conn = psycopg2.connect(DATABASE_URL)
                _pg_conn.autocommit = True
            else:
                try:
                    if _pg_conn.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_ERROR:
                        _pg_conn.rollback()
                except Exception:
                    pass
        except Exception:
            _pg_conn = psycopg2.connect(DATABASE_URL)
            _pg_conn.autocommit = True
        return _PooledPostgresWrapper(_pg_conn)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def _execute(conn, query: str, params: tuple = ()):
    """Executes a query handling SQL dialect placeholder differences (? vs %s)."""
    cur = conn.cursor()
    if _USE_POSTGRES:
        pg_query = query.replace("?", "%s")
        cur.execute(pg_query, params)
    else:
        cur.execute(query, params)
    return cur


def _fetchall_dicts(cur) -> List[Dict[str, Any]]:
    if _USE_POSTGRES:
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    else:
        return [dict(row) for row in cur.fetchall()]


def _fetchone_dict(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    if not row:
        return None
    if _USE_POSTGRES:
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row))
    else:
        return dict(row)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    if _USE_POSTGRES:
        # PostgreSQL DDL
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id       VARCHAR(32) PRIMARY KEY,
                first_name        VARCHAR(64) NOT NULL,
                last_name         VARCHAR(64) NOT NULL,
                email             VARCHAR(128) NOT NULL UNIQUE,
                phone             VARCHAR(32),
                segment           VARCHAR(32) NOT NULL,
                is_vulnerable     BOOLEAN NOT NULL DEFAULT FALSE,
                registration_date DATE NOT NULL,
                lifetime_value    NUMERIC(10, 2) NOT NULL DEFAULT 0.00
            );

            CREATE TABLE IF NOT EXISTS products (
                product_id  VARCHAR(32) PRIMARY KEY,
                name        VARCHAR(128) NOT NULL,
                category    VARCHAR(64) NOT NULL,
                price       NUMERIC(10, 2) NOT NULL,
                safety_risk BOOLEAN NOT NULL DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id      VARCHAR(32) PRIMARY KEY,
                customer_id   VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
                product_id    VARCHAR(32) NOT NULL REFERENCES products(product_id),
                order_date    VARCHAR(32) NOT NULL,
                order_value   NUMERIC(10, 2) NOT NULL,
                quantity      INTEGER NOT NULL,
                status        VARCHAR(32) NOT NULL,
                delivery_date VARCHAR(32)
            );

            CREATE TABLE IF NOT EXISTS categories (
                category_id       VARCHAR(16) PRIMARY KEY,
                name              VARCHAR(64) NOT NULL UNIQUE,
                default_sla_hours INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS priority_rules (
                rule_id             VARCHAR(16) PRIMARY KEY,
                priority            VARCHAR(16) NOT NULL UNIQUE,
                level               INTEGER NOT NULL UNIQUE,
                description         TEXT NOT NULL,
                sla_multiplier      NUMERIC(4, 2) NOT NULL,
                auto_escalate_hours INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS complaints (
                complaint_id        VARCHAR(32) PRIMARY KEY,
                customer_id         VARCHAR(32),
                order_id            VARCHAR(32),
                product_id          VARCHAR(32),
                category_id         VARCHAR(16) NOT NULL REFERENCES categories(category_id),
                category_name       VARCHAR(64) NOT NULL,
                channel             VARCHAR(32) NOT NULL,
                severity            VARCHAR(16) NOT NULL,
                priority            VARCHAR(16) NOT NULL,
                sentiment           VARCHAR(16) NOT NULL,
                status              VARCHAR(32) NOT NULL,
                created_at          VARCHAR(32) NOT NULL,
                updated_at          VARCHAR(32) NOT NULL,
                recurrence_count    INTEGER NOT NULL DEFAULT 1,
                is_safety_issue     BOOLEAN NOT NULL DEFAULT FALSE,
                is_reopened         BOOLEAN NOT NULL DEFAULT FALSE,
                parent_complaint_id VARCHAR(32),
                order_value         NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ai_classification   TEXT,
                ai_summary          TEXT
            );

            CREATE TABLE IF NOT EXISTS complaint_events (
                event_id        VARCHAR(64) PRIMARY KEY,
                complaint_id    VARCHAR(32) NOT NULL REFERENCES complaints(complaint_id),
                event_type      VARCHAR(32) NOT NULL,
                actor           VARCHAR(64) NOT NULL,
                old_state       VARCHAR(32),
                new_state       VARCHAR(32) NOT NULL,
                event_timestamp VARCHAR(32) NOT NULL,
                details         TEXT
            );

            CREATE TABLE IF NOT EXISTS assignments (
                assignment_id VARCHAR(32) PRIMARY KEY,
                complaint_id  VARCHAR(32) NOT NULL REFERENCES complaints(complaint_id),
                team          VARCHAR(64) NOT NULL,
                agent_id      VARCHAR(32) NOT NULL,
                assigned_at   VARCHAR(32) NOT NULL,
                is_current    BOOLEAN NOT NULL DEFAULT TRUE,
                reason        TEXT
            );

            CREATE TABLE IF NOT EXISTS sla_clocks (
                sla_id        VARCHAR(32) PRIMARY KEY,
                complaint_id  VARCHAR(32) NOT NULL REFERENCES complaints(complaint_id),
                sla_hours     NUMERIC(6, 2) NOT NULL,
                started_at    VARCHAR(32) NOT NULL,
                deadline_at   VARCHAR(32) NOT NULL,
                paused_at     VARCHAR(32),
                resumed_at    VARCHAR(32),
                pause_reason  TEXT,
                is_breached   BOOLEAN NOT NULL DEFAULT FALSE,
                breached_at   VARCHAR(32),
                status        VARCHAR(16) NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id    VARCHAR(64) PRIMARY KEY,
                complaint_id  VARCHAR(32) NOT NULL REFERENCES complaints(complaint_id),
                sender_type   VARCHAR(16) NOT NULL,
                message_text  TEXT NOT NULL,
                sent_at       VARCHAR(32) NOT NULL,
                is_internal   BOOLEAN NOT NULL DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS resolutions (
                resolution_id   VARCHAR(32) PRIMARY KEY,
                complaint_id    VARCHAR(32) NOT NULL REFERENCES complaints(complaint_id),
                resolution_type VARCHAR(32) NOT NULL,
                resolved_by     VARCHAR(32) NOT NULL,
                resolved_at     VARCHAR(32) NOT NULL,
                notes           TEXT,
                refund_amount   NUMERIC(10, 2) DEFAULT 0.00
            );

            CREATE TABLE IF NOT EXISTS surveys (
                survey_id     VARCHAR(32) PRIMARY KEY,
                complaint_id  VARCHAR(32) NOT NULL REFERENCES complaints(complaint_id),
                rating        INTEGER NOT NULL,
                feedback_text TEXT,
                submitted_at  VARCHAR(32) NOT NULL,
                nps_score     INTEGER
            );
        """)
        conn.commit()
        conn.close()
        print("[DB] Initialised Neon / PostgreSQL Database successfully.")
    else:
        # SQLite DDL
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id       TEXT PRIMARY KEY,
                first_name        TEXT NOT NULL,
                last_name         TEXT NOT NULL,
                email             TEXT NOT NULL UNIQUE,
                phone             TEXT,
                segment           TEXT NOT NULL,
                is_vulnerable     INTEGER NOT NULL DEFAULT 0,
                registration_date TEXT NOT NULL,
                lifetime_value    REAL NOT NULL DEFAULT 0.00
            );

            CREATE TABLE IF NOT EXISTS products (
                product_id  TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                category    TEXT NOT NULL,
                price       REAL NOT NULL,
                safety_risk INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id      TEXT PRIMARY KEY,
                customer_id   TEXT NOT NULL,
                product_id    TEXT NOT NULL,
                order_date    TEXT NOT NULL,
                order_value   REAL NOT NULL,
                quantity      INTEGER NOT NULL,
                status        TEXT NOT NULL,
                delivery_date TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );

            CREATE TABLE IF NOT EXISTS categories (
                category_id       TEXT PRIMARY KEY,
                name              TEXT NOT NULL UNIQUE,
                default_sla_hours INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS priority_rules (
                rule_id             TEXT PRIMARY KEY,
                priority            TEXT NOT NULL UNIQUE,
                level               INTEGER NOT NULL UNIQUE,
                description         TEXT NOT NULL,
                sla_multiplier      REAL NOT NULL,
                auto_escalate_hours INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS complaints (
                complaint_id        TEXT PRIMARY KEY,
                customer_id         TEXT,
                order_id            TEXT,
                product_id          TEXT,
                category_id         TEXT NOT NULL,
                category_name       TEXT NOT NULL,
                channel             TEXT NOT NULL,
                severity            TEXT NOT NULL,
                priority            TEXT NOT NULL,
                sentiment           TEXT NOT NULL,
                status              TEXT NOT NULL,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL,
                recurrence_count    INTEGER NOT NULL DEFAULT 1,
                is_safety_issue     INTEGER NOT NULL DEFAULT 0,
                is_reopened         INTEGER NOT NULL DEFAULT 0,
                parent_complaint_id TEXT,
                order_value         REAL NOT NULL DEFAULT 0.00,
                ai_classification   TEXT,
                ai_summary          TEXT,
                FOREIGN KEY (category_id) REFERENCES categories(category_id)
            );

            CREATE TABLE IF NOT EXISTS complaint_events (
                event_id        TEXT PRIMARY KEY,
                complaint_id    TEXT NOT NULL,
                event_type      TEXT NOT NULL,
                actor           TEXT NOT NULL,
                old_state       TEXT,
                new_state       TEXT NOT NULL,
                event_timestamp TEXT NOT NULL,
                details         TEXT,
                FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
            );

            CREATE TABLE IF NOT EXISTS assignments (
                assignment_id TEXT PRIMARY KEY,
                complaint_id  TEXT NOT NULL,
                team          TEXT NOT NULL,
                agent_id      TEXT NOT NULL,
                assigned_at   TEXT NOT NULL,
                is_current    INTEGER NOT NULL DEFAULT 1,
                reason        TEXT,
                FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
            );

            CREATE TABLE IF NOT EXISTS sla_clocks (
                sla_id        TEXT PRIMARY KEY,
                complaint_id  TEXT NOT NULL,
                sla_hours     REAL NOT NULL,
                started_at    TEXT NOT NULL,
                deadline_at   TEXT NOT NULL,
                paused_at     TEXT,
                resumed_at    TEXT,
                pause_reason  TEXT,
                is_breached   INTEGER NOT NULL DEFAULT 0,
                breached_at   TEXT,
                status        TEXT NOT NULL,
                FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id    TEXT PRIMARY KEY,
                complaint_id  TEXT NOT NULL,
                sender_type   TEXT NOT NULL,
                message_text  TEXT NOT NULL,
                sent_at       TEXT NOT NULL,
                is_internal   INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
            );

            CREATE TABLE IF NOT EXISTS resolutions (
                resolution_id   TEXT PRIMARY KEY,
                complaint_id    TEXT NOT NULL,
                resolution_type TEXT NOT NULL,
                resolved_by     TEXT NOT NULL,
                resolved_at     TEXT NOT NULL,
                notes           TEXT,
                refund_amount   REAL DEFAULT 0.00,
                FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
            );

            CREATE TABLE IF NOT EXISTS surveys (
                survey_id     TEXT PRIMARY KEY,
                complaint_id  TEXT NOT NULL,
                rating        INTEGER NOT NULL,
                feedback_text TEXT,
                submitted_at  TEXT NOT NULL,
                nps_score     INTEGER,
                FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
            );
        """)
        conn.commit()
        conn.close()
        print("[DB] Initialised SQLite Database: %s" % DB_PATH)


def get_next_sequence_id(table: str, id_col: str, prefix: str, padding: int = 6) -> str:
    """Returns the next strictly sequential zero-padded ID (e.g. CMP-2026-000001, ASN-000001)."""
    with _sequence_lock:
        conn = get_conn()
        cur = _execute(conn, f"SELECT {id_col} FROM {table} WHERE {id_col} LIKE ? ORDER BY LENGTH({id_col}) DESC, {id_col} DESC LIMIT 1", (f"{prefix}%",))
        row = _fetchone_dict(cur)
        cnt = 1
        if row and row.get(id_col):
            last_id = str(row[id_col])
            num_part = last_id[len(prefix):]
            try:
                cnt = int(num_part) + 1
            except ValueError:
                cnt = 1

        candidate = f"{prefix}{cnt:0{padding}d}"
        cur2 = _execute(conn, f"SELECT 1 FROM {table} WHERE {id_col} = ?", (candidate,))
        while cur2.fetchone():
            cnt += 1
            candidate = f"{prefix}{cnt:0{padding}d}"
            cur2 = _execute(conn, f"SELECT 1 FROM {table} WHERE {id_col} = ?", (candidate,))

        conn.close()
        return candidate


def clean_database():
    """Truncates all core tables to allow clean deterministic re-seeding."""
    conn = get_conn()
    cur = conn.cursor()
    tables = [
        "surveys", "resolutions", "messages", "sla_clocks",
        "assignments", "complaint_events", "complaints",
        "orders", "products", "customers", "priority_rules", "categories"
    ]
    for tbl in tables:
        try:
            if _USE_POSTGRES:
                cur.execute(f"TRUNCATE TABLE {tbl} CASCADE")
            else:
                cur.execute(f"DELETE FROM {tbl}")
        except Exception:
            pass
    conn.commit()
    conn.close()
    invalidate_analytics_cache()
    print("[DB] Cleared existing database tables for fresh deterministic seeding.")


def log_event(complaint_id: str, event_type: str, actor: str, old_state: str, new_state: str, details: str = ""):
    """Appends an immutable state change or action event with sequential zero-padded EVT-000001 ID."""
    with _sequence_lock:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        for attempt in range(10):
            event_id = get_next_sequence_id("complaint_events", "event_id", "EVT-", 6)
            conn = get_conn()
            try:
                query = """
                    INSERT INTO complaint_events (event_id, complaint_id, event_type, actor, old_state, new_state, event_timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                _execute(conn, query, (event_id, complaint_id, event_type, actor, old_state, new_state, now, details))
                conn.commit()
                conn.close()
                break
            except Exception as e:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
                if attempt == 9:
                    raise e
                time.sleep(0.05)
    invalidate_analytics_cache()


def upsert_complaint(c: dict):
    conn = get_conn()
    if _USE_POSTGRES:
        query = """
            INSERT INTO complaints VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (complaint_id) DO UPDATE SET
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at,
                priority = EXCLUDED.priority,
                ai_classification = EXCLUDED.ai_classification,
                ai_summary = EXCLUDED.ai_summary
        """
        cur = conn.cursor()
        cur.execute(query, (
            c["complaint_id"], c.get("customer_id", ""), c.get("order_id", ""), c.get("product_id", ""),
            c["category_id"], c.get("category_name", ""), c["channel"], c["severity"], c["priority"],
            c["sentiment"], c["status"], c["created_at"], c["updated_at"], c.get("recurrence_count", 1),
            bool(c.get("is_safety_issue")), bool(c.get("is_reopened")), c.get("parent_complaint_id", ""),
            float(c.get("order_value", 0.0)), c.get("ai_classification", ""), c.get("ai_summary", "")
        ))
    else:
        query = """
            INSERT INTO complaints VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(complaint_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at,
                priority = excluded.priority,
                ai_classification = excluded.ai_classification,
                ai_summary = excluded.ai_summary
        """
        _execute(conn, query, (
            c["complaint_id"], c.get("customer_id", ""), c.get("order_id", ""), c.get("product_id", ""),
            c["category_id"], c.get("category_name", ""), c["channel"], c["severity"], c["priority"],
            c["sentiment"], c["status"], c["created_at"], c["updated_at"], c.get("recurrence_count", 1),
            int(bool(c.get("is_safety_issue"))), int(bool(c.get("is_reopened"))), c.get("parent_complaint_id", ""),
            float(c.get("order_value", 0.0)), c.get("ai_classification", ""), c.get("ai_summary", "")
        ))
    conn.commit()
    conn.close()
    invalidate_analytics_cache()


def _execute_batch(conn, cur, query_sqlite: str, query_pg: str, params_list: list):
    if not params_list:
        return
    if _USE_POSTGRES:
        from psycopg2.extras import execute_batch
        execute_batch(cur, query_pg, params_list, page_size=500)
    else:
        cur.executemany(query_sqlite, params_list)


def bulk_load(data: dict):
    conn = get_conn()
    cur = conn.cursor()

    # Master reference tables first
    cat_params = [(cat["category_id"], cat["name"], cat["default_sla_hours"]) for cat in data.get("categories", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO categories VALUES (?,?,?)",
                   "INSERT INTO categories VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", cat_params)

    pr_params = [(pr["rule_id"], pr["priority"], pr["level"], pr["description"], pr["sla_multiplier"], pr["auto_escalate_hours"]) for pr in data.get("priority_rules", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO priority_rules VALUES (?,?,?,?,?,?)",
                   "INSERT INTO priority_rules VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", pr_params)

    p_params = [(p["product_id"], p["name"], p["category"], p["price"], bool(p["safety_risk"])) for p in data.get("products", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)",
                   "INSERT INTO products VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", p_params)

    c_params = [(c["customer_id"], c["first_name"], c["last_name"], c["email"], c.get("phone", ""),
                 c["segment"], bool(c["is_vulnerable"]), c["registration_date"], c["lifetime_value"]) for c in data.get("customers", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?,?,?)",
                   "INSERT INTO customers VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", c_params)

    o_params = [(o["order_id"], o["customer_id"], o["product_id"], o["order_date"],
                 o["order_value"], o["quantity"], o["status"], o.get("delivery_date", "")) for o in data.get("orders", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?,?)",
                   "INSERT INTO orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", o_params)

    cmp_params = [(cmp["complaint_id"], cmp.get("customer_id", ""), cmp.get("order_id", ""), cmp.get("product_id", ""),
                   cmp["category_id"], cmp.get("category_name", ""), cmp["channel"], cmp["severity"], cmp["priority"],
                   cmp["sentiment"], cmp["status"], cmp["created_at"], cmp["updated_at"], cmp["recurrence_count"],
                   bool(cmp["is_safety_issue"]), bool(cmp["is_reopened"]), cmp.get("parent_complaint_id", ""),
                   cmp.get("order_value", 0.0), "", "") for cmp in data.get("complaints", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO complaints VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   "INSERT INTO complaints VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", cmp_params)

    a_params = [(a["assignment_id"], a["complaint_id"], a["team"], a["agent_id"], a["assigned_at"],
                 bool(a["is_current"]), a.get("reason", "")) for a in data.get("assignments", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO assignments VALUES (?,?,?,?,?,?,?)",
                   "INSERT INTO assignments VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", a_params)

    s_params = [(s["sla_id"], s["complaint_id"], s["sla_hours"], s["started_at"], s["deadline_at"],
                 s.get("paused_at", ""), s.get("resumed_at", ""), s.get("pause_reason", ""),
                 bool(s["is_breached"]), s.get("breached_at", ""), s["status"]) for s in data.get("sla_clocks", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO sla_clocks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   "INSERT INTO sla_clocks VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", s_params)

    m_params = [(m["message_id"], m["complaint_id"], m["sender_type"], m["message_text"], m["sent_at"],
                 bool(m["is_internal"])) for m in data.get("messages", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?)",
                   "INSERT INTO messages VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", m_params)

    r_params = [(r["resolution_id"], r["complaint_id"], r["resolution_type"], r["resolved_by"],
                 r["resolved_at"], r.get("notes", ""), r.get("refund_amount", 0.0) or 0.0) for r in data.get("resolutions", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO resolutions VALUES (?,?,?,?,?,?,?)",
                   "INSERT INTO resolutions VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", r_params)

    sv_params = [(sv["survey_id"], sv["complaint_id"], sv["rating"], sv.get("feedback_text", ""),
                  sv["submitted_at"], sv.get("nps_score", 0) or 0) for sv in data.get("surveys", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO surveys VALUES (?,?,?,?,?,?)",
                   "INSERT INTO surveys VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", sv_params)

    evt_params = [(evt["event_id"], evt["complaint_id"], evt["event_type"], evt["actor"],
                   evt.get("old_state", ""), evt["new_state"], evt["event_timestamp"], evt.get("details", "")) for evt in data.get("complaint_events", [])]
    _execute_batch(conn, cur, "INSERT OR IGNORE INTO complaint_events VALUES (?,?,?,?,?,?,?,?)",
                   "INSERT INTO complaint_events VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", evt_params)

    conn.commit()
    conn.close()
    invalidate_analytics_cache()
    print("[DB] Bulk loading complete into %s" % ("PostgreSQL" if _USE_POSTGRES else "SQLite"))


def get_complaint(complaint_id: str):
    conn = get_conn()
    cur = _execute(conn, "SELECT * FROM complaints WHERE complaint_id = ?", (complaint_id,))
    res = _fetchone_dict(cur)
    conn.close()
    return res


def list_complaints(status: str = None, priority: str = None, category_id: str = None, limit: int = 50, offset: int = 0):
    conn = get_conn()
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if category_id:
        query += " AND category_id = ?"
        params.append(category_id)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur = _execute(conn, query, tuple(params))
    rows = _fetchall_dicts(cur)
    conn.close()
    return rows


def update_complaint_status(complaint_id: str, new_status: str, actor: str = "System"):
    c = get_complaint(complaint_id)
    old_status = c.get("status") if c else "Unknown"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    conn = get_conn()
    _execute(conn, "UPDATE complaints SET status = ?, updated_at = ? WHERE complaint_id = ?",
             (new_status, now, complaint_id))
    conn.commit()
    conn.close()
    invalidate_analytics_cache()

    # Log immutable event history
    log_event(complaint_id, "STATUS_CHANGED", actor, old_status, new_status, "Status updated from %s to %s" % (old_status, new_status))


def assign_complaint(complaint_id: str, team: str, agent_id: str, actor: str = "System", reason: str = ""):
    with _sequence_lock:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        for attempt in range(10):
            new_asn_id = get_next_sequence_id("assignments", "assignment_id", "ASN-", 6)
            conn = get_conn()
            try:
                # Deactivate current assignment
                _execute(conn, "UPDATE assignments SET is_current = FALSE WHERE complaint_id = ?", (complaint_id,))

                # Create new assignment with sequential zero-padded ASN-000001 ID
                _execute(conn, "INSERT INTO assignments VALUES (?,?,?,?,?,?,?)",
                         (new_asn_id, complaint_id, team, agent_id, now, True, reason))
                conn.commit()
                conn.close()
                break
            except Exception as e:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
                if attempt == 9:
                    raise e
                time.sleep(0.05)
    invalidate_analytics_cache()

    log_event(complaint_id, "ASSIGNED", actor, "", team, "Assigned to %s (Agent: %s). %s" % (team, agent_id, reason))


def get_complaint_events(complaint_id: str) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = _execute(conn, "SELECT * FROM complaint_events WHERE complaint_id = ? ORDER BY event_timestamp ASC", (complaint_id,))
    events = _fetchall_dicts(cur)
    conn.close()
    return events


def get_assignments(complaint_id: str) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = _execute(conn, "SELECT * FROM assignments WHERE complaint_id = ? ORDER BY assigned_at DESC", (complaint_id,))
    asns = _fetchall_dicts(cur)
    conn.close()
    return asns


def get_assignment(complaint_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = _execute(conn, "SELECT * FROM assignments WHERE complaint_id = ? AND is_current = TRUE", (complaint_id,))
    asn = _fetchone_dict(cur)
    conn.close()
    return asn


def get_sla(complaint_id: str):
    conn = get_conn()
    cur = _execute(conn, "SELECT * FROM sla_clocks WHERE complaint_id = ?", (complaint_id,))
    sla = _fetchone_dict(cur)
    conn.close()
    return sla


def get_resolution(complaint_id: str):
    conn = get_conn()
    cur = _execute(conn, "SELECT * FROM resolutions WHERE complaint_id = ?", (complaint_id,))
    res = _fetchone_dict(cur)
    conn.close()
    return res


def get_survey(complaint_id: str):
    conn = get_conn()
    cur = _execute(conn, "SELECT * FROM surveys WHERE complaint_id = ?", (complaint_id,))
    sv = _fetchone_dict(cur)
    conn.close()
    return sv


def get_messages(complaint_id: str):
    conn = get_conn()
    cur = _execute(conn, "SELECT * FROM messages WHERE complaint_id = ? ORDER BY sent_at ASC", (complaint_id,))
    msgs = _fetchall_dicts(cur)
    conn.close()
    return msgs


def add_message(complaint_id: str, sender_type: str, text: str, is_internal: bool = False):
    conn = get_conn()
    cur = _execute(conn, "SELECT COUNT(*) as cnt FROM messages WHERE complaint_id = ?", (complaint_id,))
    row = _fetchone_dict(cur)
    cnt = ((row["cnt"] if row else 0) or 0) + 1
    msg_id = f"MSG-{complaint_id}-{cnt:03d}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    _execute(conn, "INSERT INTO messages VALUES (?,?,?,?,?,?)",
             (msg_id, complaint_id, sender_type, text, now, bool(is_internal)))
    conn.commit()
    conn.close()
    invalidate_analytics_cache()

    log_event(complaint_id, "MESSAGE_SENT" if sender_type != "Customer" else "MESSAGE_RECEIVED",
              sender_type, "", "", "Message sent by %s: %s" % (sender_type, text[:60]))
    return {"message_id": msg_id, "complaint_id": complaint_id, "sent_at": now}


_ANALYTICS_CACHE = None
_ANALYTICS_CACHE_TIME = 0.0


def invalidate_analytics_cache():
    global _ANALYTICS_CACHE
    _ANALYTICS_CACHE = None


def get_analytics(force_refresh: bool = False):
    global _ANALYTICS_CACHE, _ANALYTICS_CACHE_TIME
    import time
    now_ts = time.time()
    if not force_refresh and _ANALYTICS_CACHE is not None and (now_ts - _ANALYTICS_CACHE_TIME < 15.0):
        return _ANALYTICS_CACHE

    conn = get_conn()
    cur = _execute(conn, "SELECT COUNT(*) as total, SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved FROM complaints")
    totals = _fetchone_dict(cur) or {"total": 0, "resolved": 0}

    cur = _execute(conn, "SELECT COUNT(*) as breached FROM sla_clocks WHERE is_breached = TRUE OR status = 'Breached'")
    sla_row = _fetchone_dict(cur) or {"breached": 0}

    cur = _execute(conn, "SELECT AVG(rating) as avg_csat, AVG(nps_score) as avg_nps FROM surveys")
    survey_row = _fetchone_dict(cur) or {"avg_csat": 0.0, "avg_nps": 0.0}

    cur = _execute(conn, "SELECT priority, COUNT(*) as count FROM complaints GROUP BY priority")
    priority_dist = _fetchall_dicts(cur)

    cur = _execute(conn, "SELECT category_name, COUNT(*) as count FROM complaints GROUP BY category_name")
    category_dist = _fetchall_dicts(cur)

    conn.close()

    total = int(totals["total"] or 0)
    resolved = int(totals["resolved"] or 0)
    breached = int(sla_row["breached"] or 0)
    open_count = total - resolved

    res = {
        "total_complaints": total,
        "open_complaints": open_count,
        "resolved_complaints": resolved,
        "breached_slas": breached,
        "sla_breach_rate_pct": float(round((breached / total * 100), 2)) if total > 0 else 0.0,
        "avg_csat_rating": float(round(float(survey_row["avg_csat"] or 0.0), 2)),
        "avg_nps_score": float(round(float(survey_row["avg_nps"] or 0.0), 2)),
        "priority_distribution": priority_dist,
        "category_distribution": category_dist,
    }
    _ANALYTICS_CACHE = res
    _ANALYTICS_CACHE_TIME = now_ts
    return res
