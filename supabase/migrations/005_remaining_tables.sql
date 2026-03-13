-- ============================================================================
-- Pan-African Microfinance SaaS — Supabase Migration v3.0
-- Part 5: GL, Compliance, Investors, MoMo, Notifications, Reports,
--          Onboarding, Integrations, Sync Queue, Audit Tables
-- ============================================================================

-- ======================== GENERAL LEDGER ========================

CREATE TABLE public.gl_accounts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    account_code            VARCHAR(20) NOT NULL,
    account_name            VARCHAR(255) NOT NULL,
    account_type            VARCHAR(20) NOT NULL
                            CHECK (account_type IN ('ASSET','LIABILITY','EQUITY','INCOME','EXPENSE')),
    parent_account_id       UUID REFERENCES gl_accounts(id),
    is_header               BOOLEAN NOT NULL DEFAULT FALSE,
    is_system_account       BOOLEAN NOT NULL DEFAULT FALSE,
    normal_balance          CHAR(1) NOT NULL CHECK (normal_balance IN ('D','C')),
    currency                CHAR(3) NOT NULL,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    regulatory_mapping_code VARCHAR(50) DEFAULT '',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, account_code)
);

CREATE TABLE public.accounting_periods (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period_name VARCHAR(50) NOT NULL,
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CLOSING','CLOSED')),
    closed_by   UUID REFERENCES users(id),
    closed_at   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, period_name)
);

CREATE TABLE public.gl_transactions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    transaction_ref         VARCHAR(50) NOT NULL,
    transaction_date        DATE NOT NULL,
    period_id               UUID NOT NULL REFERENCES accounting_periods(id),
    description             TEXT DEFAULT '',
    source_type             VARCHAR(30) DEFAULT '',
    source_id               UUID,
    posted_by               UUID NOT NULL REFERENCES users(id),
    is_reversal             BOOLEAN NOT NULL DEFAULT FALSE,
    reverses_transaction_id UUID REFERENCES gl_transactions(id),
    sync_id                 UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status             VARCHAR(20) NOT NULL DEFAULT 'SYNCED',
    device_id               VARCHAR(100) DEFAULT '',
    client_created_at       TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gl_txn_period ON gl_transactions(tenant_id, period_id);

CREATE TABLE public.gl_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    transaction_id  UUID NOT NULL REFERENCES gl_transactions(id) ON DELETE CASCADE,
    account_id      UUID NOT NULL REFERENCES gl_accounts(id),
    debit_amount    NUMERIC(19,4) NOT NULL DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount   NUMERIC(19,4) NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),
    currency        CHAR(3) NOT NULL,
    description     TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (debit_amount > 0 OR credit_amount > 0),
    CHECK (NOT (debit_amount > 0 AND credit_amount > 0))
);

CREATE INDEX idx_gl_entries_account ON gl_entries(tenant_id, account_id);

CREATE TABLE public.exchange_rates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_currency   CHAR(3) NOT NULL,
    target_currency CHAR(3) NOT NULL,
    rate            NUMERIC(19,8) NOT NULL,
    rate_date       DATE NOT NULL,
    source          VARCHAR(50) DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (base_currency, target_currency, rate_date)
);

-- ======================== COMPLIANCE & AML ========================

CREATE TABLE public.aml_alerts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id               UUID NOT NULL REFERENCES clients(id),
    alert_type              VARCHAR(50) NOT NULL,
    trigger_description     TEXT NOT NULL,
    trigger_amount          NUMERIC(19,4),
    trigger_currency        CHAR(3) DEFAULT '',
    source_transaction_id   UUID,
    status                  VARCHAR(20) NOT NULL DEFAULT 'OPEN'
                            CHECK (status IN ('OPEN','UNDER_REVIEW','ESCALATED','STR_FILED','CLOSED_NO_ACTION')),
    assigned_to             UUID REFERENCES users(id),
    risk_score              INT,
    review_notes            TEXT DEFAULT '',
    escalated_at            TIMESTAMPTZ,
    closed_at               TIMESTAMPTZ,
    closed_by               UUID REFERENCES users(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_aml_open ON aml_alerts(tenant_id, status) WHERE status IN ('OPEN','UNDER_REVIEW','ESCALATED');

CREATE TABLE public.strs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    alert_id                UUID REFERENCES aml_alerts(id),
    client_id               UUID NOT NULL REFERENCES clients(id),
    report_type             VARCHAR(10) NOT NULL CHECK (report_type IN ('STR','CTR')),
    narrative               TEXT NOT NULL,
    transaction_amount      NUMERIC(19,4),
    transaction_currency    CHAR(3) DEFAULT '',
    transaction_date        DATE,
    status                  VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
                            CHECK (status IN ('DRAFT','SUBMITTED','ACKNOWLEDGED','REJECTED_BY_FIC')),
    submitted_to            VARCHAR(100) DEFAULT '',
    submitted_at            TIMESTAMPTZ,
    fic_reference           VARCHAR(100) DEFAULT '',
    filed_by                UUID NOT NULL REFERENCES users(id),
    approved_by             UUID REFERENCES users(id),
    deadline                DATE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.transaction_monitoring_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code    CHAR(2) NOT NULL REFERENCES country_packs(country_code),
    rule_code       VARCHAR(50) NOT NULL,
    rule_name       VARCHAR(255) NOT NULL,
    rule_type       VARCHAR(30) NOT NULL CHECK (rule_type IN ('THRESHOLD','PATTERN','VELOCITY')),
    config          JSONB NOT NULL,
    severity        VARCHAR(10) NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.prudential_returns (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    return_template_code    VARCHAR(50) NOT NULL,
    return_name             VARCHAR(255) NOT NULL,
    reporting_period        VARCHAR(20) NOT NULL,
    due_date                DATE NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                            CHECK (status IN ('PENDING','GENERATED','REVIEWED','SUBMITTED','OVERDUE')),
    data                    JSONB,
    system_computed_values  JSONB,
    submitted_values        JSONB,
    variance_pct            NUMERIC(5,2),
    generated_by            UUID REFERENCES users(id),
    generated_at            TIMESTAMPTZ,
    submitted_by            UUID REFERENCES users(id),
    submitted_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ======================== INVESTORS ========================

CREATE TABLE public.investor_profiles (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id                     UUID NOT NULL REFERENCES users(id),
    investor_name               VARCHAR(255) NOT NULL,
    investor_type               VARCHAR(20) NOT NULL CHECK (investor_type IN ('INDIVIDUAL','INSTITUTIONAL','FUND')),
    investment_currency         CHAR(3) NOT NULL,
    invested_amount             NUMERIC(19,4) NOT NULL,
    invested_amount_local       NUMERIC(19,4) NOT NULL,
    investment_date             DATE NOT NULL,
    exchange_rate_at_investment NUMERIC(19,8) NOT NULL,
    current_value_local         NUMERIC(19,4),
    status                      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                                CHECK (status IN ('ACTIVE','SUSPENDED','EXITED')),
    covenant_thresholds         JSONB,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.investor_share_links (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    investor_profile_id UUID REFERENCES investor_profiles(id),
    token               VARCHAR(128) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) DEFAULT '',
    expires_at          TIMESTAMPTZ,
    max_views           INT,
    view_count          INT NOT NULL DEFAULT 0,
    created_by          UUID NOT NULL REFERENCES users(id),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.dividends (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    investor_id     UUID NOT NULL REFERENCES investor_profiles(id),
    period          VARCHAR(20) NOT NULL,
    declared_rate_pct NUMERIC(7,4) NOT NULL,
    amount          NUMERIC(19,4) NOT NULL,
    currency        CHAR(3) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'DECLARED'
                    CHECK (status IN ('DECLARED','APPROVED','PAID','REINVESTED')),
    paid_at         TIMESTAMPTZ,
    approved_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ======================== MOBILE MONEY ========================

CREATE TABLE public.mobile_money_providers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code        CHAR(2) NOT NULL REFERENCES country_packs(country_code),
    provider_code       VARCHAR(30) NOT NULL,
    provider_name       VARCHAR(100) NOT NULL,
    api_type            VARCHAR(30) NOT NULL,
    api_config          JSONB NOT NULL DEFAULT '{}',
    currency            CHAR(3) NOT NULL,
    phone_prefix        VARCHAR(10) DEFAULT '',
    phone_regex         VARCHAR(100) DEFAULT '',
    min_transaction     NUMERIC(19,4),
    max_transaction     NUMERIC(19,4),
    fee_structure       JSONB DEFAULT '{}',
    settlement_gl_account_id UUID REFERENCES gl_accounts(id),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (country_code, provider_code)
);

CREATE TABLE public.mobile_money_transactions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider_id             UUID NOT NULL REFERENCES mobile_money_providers(id),
    transaction_type        VARCHAR(20) NOT NULL
                            CHECK (transaction_type IN ('COLLECTION','DISBURSEMENT','DEPOSIT','WITHDRAWAL','REVERSAL')),
    direction               CHAR(2) NOT NULL CHECK (direction IN ('IN','OUT')),
    phone_number            VARCHAR(20) NOT NULL,
    amount                  NUMERIC(19,4) NOT NULL,
    currency                CHAR(3) NOT NULL,
    fee_amount              NUMERIC(19,4) DEFAULT 0,
    fee_bearer              VARCHAR(10) DEFAULT 'CLIENT',
    client_id               UUID REFERENCES clients(id),
    loan_id                 UUID REFERENCES loans(id),
    deposit_account_id      UUID REFERENCES deposit_accounts(id),
    repayment_id            UUID REFERENCES repayments(id),
    provider_reference      VARCHAR(100) DEFAULT '',
    internal_reference      VARCHAR(100) NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'INITIATED'
                            CHECK (status IN ('INITIATED','PENDING','SUCCESS','FAILED','REVERSED','TIMEOUT')),
    status_message          TEXT DEFAULT '',
    initiated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at            TIMESTAMPTZ,
    reconciled              BOOLEAN NOT NULL DEFAULT FALSE,
    reconciled_at           TIMESTAMPTZ,
    gl_transaction_id       UUID,
    initiated_by            UUID NOT NULL REFERENCES users(id),
    sync_id                 UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status             VARCHAR(20) NOT NULL DEFAULT 'SYNCED',
    device_id               VARCHAR(100) DEFAULT '',
    client_created_at       TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_momo_status ON mobile_money_transactions(tenant_id, status)
    WHERE status IN ('INITIATED','PENDING');
CREATE INDEX idx_momo_reconcile ON mobile_money_transactions(tenant_id, reconciled)
    WHERE reconciled = FALSE;

CREATE TABLE public.mobile_money_reconciliation (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider_id         UUID NOT NULL REFERENCES mobile_money_providers(id),
    reconciliation_date DATE NOT NULL,
    statement_file_path TEXT DEFAULT '',
    statement_total     NUMERIC(19,4),
    statement_count     INT,
    system_total        NUMERIC(19,4),
    system_count        INT,
    matched_count       INT NOT NULL DEFAULT 0,
    unmatched_system    INT NOT NULL DEFAULT 0,
    unmatched_provider  INT NOT NULL DEFAULT 0,
    variance_amount     NUMERIC(19,4) DEFAULT 0,
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETED','EXCEPTION')),
    completed_by        UUID REFERENCES users(id),
    completed_at        TIMESTAMPTZ,
    notes               TEXT DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ======================== NOTIFICATIONS & SMS ========================

CREATE TABLE public.notification_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rule_code       VARCHAR(50) NOT NULL,
    rule_name       VARCHAR(255) NOT NULL,
    metric          VARCHAR(50) NOT NULL,
    operator        VARCHAR(5) NOT NULL CHECK (operator IN ('GT','LT','GTE','LTE','EQ')),
    threshold_value NUMERIC(19,4) NOT NULL,
    severity        VARCHAR(10) NOT NULL CHECK (severity IN ('INFO','WARNING','CRITICAL')),
    notify_roles    JSONB NOT NULL DEFAULT '[]',
    notify_email    BOOLEAN NOT NULL DEFAULT FALSE,
    notify_sms      BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id),
    rule_id         UUID REFERENCES notification_rules(id),
    severity        VARCHAR(10) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    message         TEXT NOT NULL,
    link            VARCHAR(500) DEFAULT '',
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMPTZ,
    dismissed       BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_by    UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notif_unread ON notifications(tenant_id, user_id, is_read) WHERE is_read = FALSE;

CREATE TABLE public.sms_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code    CHAR(2) NOT NULL REFERENCES country_packs(country_code),
    tenant_id       UUID REFERENCES tenants(id),
    template_code   VARCHAR(50) NOT NULL,
    language        CHAR(5) NOT NULL DEFAULT 'en',
    message_body    TEXT NOT NULL,
    max_sms_parts   INT NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.sms_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    template_id         UUID REFERENCES sms_templates(id),
    recipient_phone     VARCHAR(20) NOT NULL,
    recipient_client_id UUID REFERENCES clients(id),
    recipient_user_id   UUID REFERENCES users(id),
    message_body        TEXT NOT NULL,
    sms_parts           INT NOT NULL DEFAULT 1,
    provider            VARCHAR(30) NOT NULL,
    provider_message_id VARCHAR(100) DEFAULT '',
    status              VARCHAR(20) NOT NULL DEFAULT 'QUEUED'
                        CHECK (status IN ('QUEUED','SENT','DELIVERED','FAILED','REJECTED')),
    status_message      TEXT DEFAULT '',
    cost_amount         NUMERIC(8,4),
    cost_currency       CHAR(3) DEFAULT '',
    sent_at             TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    triggered_by        VARCHAR(30) DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.ussd_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id),
    session_id      VARCHAR(100) NOT NULL,
    phone_number    VARCHAR(20) NOT NULL,
    client_id       UUID REFERENCES clients(id),
    service_code    VARCHAR(20) NOT NULL,
    current_level   INT NOT NULL DEFAULT 0,
    session_data    JSONB DEFAULT '{}',
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE','COMPLETED','TIMEOUT','ERROR')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    last_input      TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ======================== REPORTS ========================

CREATE TABLE public.report_definitions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_code     VARCHAR(50) NOT NULL UNIQUE,
    report_name     VARCHAR(255) NOT NULL,
    description     TEXT DEFAULT '',
    category        VARCHAR(30) NOT NULL,
    applicable_roles JSONB NOT NULL DEFAULT '[]',
    parameters      JSONB NOT NULL DEFAULT '[]',
    output_formats  JSONB NOT NULL DEFAULT '["PDF","XLSX","CSV"]',
    template_path   TEXT DEFAULT '',
    query_config    JSONB,
    is_system       BOOLEAN NOT NULL DEFAULT TRUE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.report_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    report_id       UUID NOT NULL REFERENCES report_definitions(id),
    schedule_name   VARCHAR(255) NOT NULL,
    frequency       VARCHAR(20) NOT NULL CHECK (frequency IN ('DAILY','WEEKLY','MONTHLY','QUARTERLY','ANNUAL')),
    day_of_week     INT,
    day_of_month    INT,
    time_of_day     TIME NOT NULL DEFAULT '06:00:00',
    parameters      JSONB DEFAULT '{}',
    output_format   VARCHAR(10) NOT NULL DEFAULT 'PDF',
    recipients      JSONB NOT NULL DEFAULT '[]',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    next_run_at     TIMESTAMPTZ NOT NULL,
    last_run_at     TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.report_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    report_id       UUID NOT NULL REFERENCES report_definitions(id),
    schedule_id     UUID REFERENCES report_schedules(id),
    parameters      JSONB NOT NULL DEFAULT '{}',
    output_format   VARCHAR(10) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'QUEUED'
                    CHECK (status IN ('QUEUED','GENERATING','COMPLETED','FAILED')),
    file_path       TEXT DEFAULT '',
    file_size_bytes BIGINT,
    page_count      INT,
    generation_time_ms INT,
    error_message   TEXT DEFAULT '',
    generated_by    UUID REFERENCES users(id),
    generated_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_report_runs_recent ON report_runs(tenant_id, created_at DESC);

-- ======================== ONBOARDING & IMPORT ========================

CREATE TABLE public.onboarding_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    steps           JSONB NOT NULL DEFAULT '[]',
    is_complete     BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    skipped_steps   JSONB DEFAULT '[]',
    load_demo_data  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.import_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    import_type     VARCHAR(30) NOT NULL,
    file_path       TEXT NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT,
    status          VARCHAR(20) NOT NULL DEFAULT 'UPLOADED',
    total_rows      INT,
    valid_rows      INT,
    error_rows      INT,
    warning_rows    INT,
    validation_errors JSONB DEFAULT '[]',
    validation_warnings JSONB DEFAULT '[]',
    imported_count  INT DEFAULT 0,
    skipped_count   INT DEFAULT 0,
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ======================== API & WEBHOOKS ========================

CREATE TABLE public.api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key_prefix      VARCHAR(8) NOT NULL,
    key_hash        VARCHAR(255) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    permissions     JSONB NOT NULL DEFAULT '[]',
    rate_limit_per_minute INT NOT NULL DEFAULT 60,
    allowed_ips     JSONB DEFAULT '[]',
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.webhooks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type      VARCHAR(50) NOT NULL,
    target_url      TEXT NOT NULL,
    secret_hash     VARCHAR(255) NOT NULL,
    headers         JSONB DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    retry_count     INT NOT NULL DEFAULT 3,
    retry_delay_seconds INT NOT NULL DEFAULT 60,
    last_triggered_at TIMESTAMPTZ,
    last_status_code INT,
    consecutive_failures INT NOT NULL DEFAULT 0,
    disabled_at     TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.webhook_deliveries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id      UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event_type      VARCHAR(50) NOT NULL,
    payload         JSONB NOT NULL,
    response_status INT,
    response_body   TEXT DEFAULT '',
    response_time_ms INT,
    attempt_number  INT NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING','SUCCESS','FAILED','RETRYING')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ======================== SYNC QUEUE ========================

CREATE TABLE public.sync_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id),
    device_id       VARCHAR(100) NOT NULL,
    target_table    VARCHAR(100) NOT NULL,
    target_sync_id  UUID NOT NULL,
    operation       VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT','UPDATE')),
    payload         JSONB NOT NULL,
    client_timestamp TIMESTAMPTZ NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'QUEUED'
                    CHECK (status IN ('QUEUED','PROCESSING','APPLIED','CONFLICT','REJECTED')),
    error_message   TEXT DEFAULT '',
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sync_pending ON sync_queue(tenant_id, status) WHERE status = 'QUEUED';

-- ======================== AUDIT TABLES ========================

CREATE TABLE audit.logs (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    user_id         UUID,
    user_email      VARCHAR(255) DEFAULT '',
    user_role       VARCHAR(50) DEFAULT '',
    action          VARCHAR(20) NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     UUID,
    old_values      JSONB,
    new_values      JSONB,
    changed_fields  JSONB,
    justification   TEXT DEFAULT '',
    ip_address      INET,
    user_agent      TEXT DEFAULT '',
    session_id      VARCHAR(100) DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_tenant_date ON audit.logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit.logs(tenant_id, resource_type, resource_id);
CREATE INDEX idx_audit_user ON audit.logs(tenant_id, user_id);

CREATE TABLE audit.login_attempts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID,
    email           VARCHAR(255) NOT NULL,
    success         BOOLEAN NOT NULL,
    failure_reason  VARCHAR(50) DEFAULT '',
    ip_address      INET,
    user_agent      TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Restrict audit tables: app role can only INSERT and SELECT
-- (Run as superuser / Supabase dashboard)
-- REVOKE UPDATE, DELETE ON audit.logs FROM authenticated;
-- REVOKE UPDATE, DELETE ON audit.login_attempts FROM authenticated;
