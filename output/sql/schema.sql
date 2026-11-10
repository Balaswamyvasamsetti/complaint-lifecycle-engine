-- schema.sql — Complaint Management Engine DDL (PostgreSQL & SQLite compatible)

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

CREATE INDEX IF NOT EXISTS idx_complaints_customer ON complaints(customer_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints(priority);
CREATE INDEX IF NOT EXISTS idx_events_complaint ON complaint_events(complaint_id);
CREATE INDEX IF NOT EXISTS idx_assignments_complaint ON assignments(complaint_id);
CREATE INDEX IF NOT EXISTS idx_messages_complaint ON messages(complaint_id);
