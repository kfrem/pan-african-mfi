# Pan-African Microfinance SaaS — Database Schema Specification v3.0 (FINAL)
## Supabase + Railway + Next.js PWA | Offline Sync | Full Feature Set

---

### Architecture Summary

| Layer | Technology | Cost |
|---|---|---|
| Database + Auth + Storage | Supabase Pro | ~£28/mo (existing) |
| Backend API + Task Queue | Django + DRF + Celery on Railway | ~$5/mo |
| Frontend | Next.js PWA on Vercel free tier | $0 |
| SMS + USSD | Africa's Talking | ~$10-20/mo usage |
| Email | Resend free tier | $0 |
| CI/CD | GitHub Actions free tier | $0 |
| **Total** | | **~£35-40/mo** |

---

### Table Count Summary

| Domain | Tables | New in v3 |
|---|---|---|
| 1. Tenants & Config | 6 | — |
| 2. Auth & RBAC | 9 | +1 (active_sessions) |
| 3. Clients & KYC | 5 | +1 (credit_scores) |
| 4. Loans & Repayments | 4 | — |
| 5. Deposits | 3 | — |
| 6. General Ledger | 4 | — |
| 7. Compliance & AML | 4 | — |
| 8. Investors | 3 | — |
| 9. Audit | 2 | — |
| 10. Notifications & SMS | 4 | +2 (sms_templates, sms_log) |
| 11. Mobile Money (NEW) | 3 | +3 |
| 12. Credit Scoring (NEW) | 2 | +2 |
| 13. Reports (NEW) | 3 | +3 |
| 14. Onboarding & Import (NEW) | 2 | +2 |
| 15. API & Webhooks (NEW) | 2 | +2 |
| 16. Sync | 1 | — |
| **TOTAL** | **57** | **+16 new** |

---

## Domains 1-9: Unchanged from v2

All tables from the v2 schema specification remain exactly as defined. The following sections document ONLY the new and modified tables added in v3.

---

## Domain 2 (Addition): Session Management

### active_sessions
```sql
CREATE TABLE public.active_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    user_id             UUID NOT NULL REFERENCES users(id),
    session_token_hash  VARCHAR(255) NOT NULL, -- hash of JWT/session token
    device_type         VARCHAR(20), -- DESKTOP, TABLET, MOBILE
    device_info         TEXT, -- browser/OS user agent parsed
    ip_address          INET NOT NULL,
    location_country    CHAR(2), -- GeoIP lookup
    location_city       VARCHAR(100),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    terminated_by       UUID REFERENCES users(id), -- if admin killed session
    terminated_reason   VARCHAR(50), -- LOGOUT, TIMEOUT, ADMIN_KILL, SUSPICIOUS
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_active ON active_sessions(tenant_id, user_id, is_active)
    WHERE is_active = TRUE;
CREATE INDEX idx_sessions_ip ON active_sessions(tenant_id, ip_address);
```

### ip_whitelist (per tenant, optional)
```sql
CREATE TABLE public.ip_whitelists (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    ip_range    CIDR NOT NULL, -- supports single IP or subnet
    description VARCHAR(255), -- e.g. "Head Office", "Branch A WiFi"
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_by  UUID NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### session_configs (per tenant, per role)
```sql
CREATE TABLE public.session_configs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    role_code               VARCHAR(50), -- NULL = applies to all roles
    session_timeout_minutes INT NOT NULL DEFAULT 480, -- 8 hours default
    max_concurrent_sessions INT NOT NULL DEFAULT 3,
    require_ip_whitelist    BOOLEAN NOT NULL DEFAULT FALSE,
    require_mfa             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, role_code)
);

-- Default configs seeded per tenant:
-- INVESTOR: timeout=15min, max_sessions=2, require_mfa=TRUE
-- BOARD_DIRECTOR: timeout=30min, max_sessions=2, require_mfa=TRUE
-- CEO_CFO: timeout=60min, max_sessions=2, require_mfa=TRUE
-- LOAN_OFFICER: timeout=480min (8hr), max_sessions=1
-- IT_SECURITY_ADMIN: timeout=30min, require_mfa=TRUE, require_ip_whitelist=TRUE
```

---

## Domain 11 (NEW): Mobile Money

Provider-agnostic design — any mobile money provider in any country can be added via configuration.

### mobile_money_providers
```sql
CREATE TABLE public.mobile_money_providers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code        CHAR(2) NOT NULL REFERENCES country_packs(country_code),
    provider_code       VARCHAR(30) NOT NULL, -- MTN_MOMO_GH, VODAFONE_CASH_GH, AIRTEL_ZM etc
    provider_name       VARCHAR(100) NOT NULL, -- "MTN Mobile Money"
    api_type            VARCHAR(30) NOT NULL, -- AFRICAS_TALKING, DIRECT_API, MANUAL
    api_config          JSONB NOT NULL DEFAULT '{}', -- encrypted credentials, endpoints, callback URLs
    currency            CHAR(3) NOT NULL,
    phone_prefix        VARCHAR(10), -- e.g. "+233" for Ghana
    phone_regex         VARCHAR(100), -- validation pattern for phone numbers
    min_transaction     NUMERIC(19,4), -- provider minimum
    max_transaction     NUMERIC(19,4), -- provider maximum
    fee_structure       JSONB DEFAULT '{}', -- how fees are calculated
    settlement_gl_account_id UUID REFERENCES gl_accounts(id), -- GL mapping
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (country_code, provider_code)
);
```

### mobile_money_transactions
```sql
CREATE TABLE public.mobile_money_transactions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    provider_id             UUID NOT NULL REFERENCES mobile_money_providers(id),
    transaction_type        VARCHAR(20) NOT NULL
                            CHECK (transaction_type IN (
                                'COLLECTION', -- repayment received via momo
                                'DISBURSEMENT', -- loan paid out via momo
                                'DEPOSIT', -- savings deposit via momo
                                'WITHDRAWAL', -- savings withdrawal via momo
                                'REVERSAL'
                            )),
    direction               CHAR(2) NOT NULL CHECK (direction IN ('IN','OUT')),
    phone_number            VARCHAR(20) NOT NULL,
    amount                  NUMERIC(19,4) NOT NULL,
    currency                CHAR(3) NOT NULL,
    fee_amount              NUMERIC(19,4) DEFAULT 0, -- provider fee
    fee_bearer              VARCHAR(10) DEFAULT 'CLIENT' CHECK (fee_bearer IN ('CLIENT','MFI')),
    -- Linking to business records
    client_id               UUID REFERENCES clients(id),
    loan_id                 UUID REFERENCES loans(id),
    deposit_account_id      UUID REFERENCES deposit_accounts(id),
    repayment_id            UUID REFERENCES repayments(id),
    -- Provider references
    provider_reference      VARCHAR(100), -- their transaction ID
    internal_reference      VARCHAR(100) NOT NULL, -- our transaction ID
    -- Status tracking
    status                  VARCHAR(20) NOT NULL DEFAULT 'INITIATED'
                            CHECK (status IN ('INITIATED','PENDING','SUCCESS','FAILED','REVERSED','TIMEOUT')),
    status_message          TEXT,
    initiated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at            TIMESTAMPTZ,
    -- Reconciliation
    reconciled              BOOLEAN NOT NULL DEFAULT FALSE,
    reconciled_at           TIMESTAMPTZ,
    gl_transaction_id       UUID, -- linked GL entry after reconciliation
    -- Who initiated
    initiated_by            UUID NOT NULL REFERENCES users(id),
    -- Offline sync (collections can happen offline, queued for processing)
    sync_id                 UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status             VARCHAR(20) NOT NULL DEFAULT 'SYNCED',
    device_id               VARCHAR(100),
    client_created_at       TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_momo_status ON mobile_money_transactions(tenant_id, status)
    WHERE status IN ('INITIATED','PENDING');
CREATE INDEX idx_momo_reconcile ON mobile_money_transactions(tenant_id, reconciled)
    WHERE reconciled = FALSE;
CREATE INDEX idx_momo_provider_ref ON mobile_money_transactions(provider_id, provider_reference);
```

### mobile_money_reconciliation
```sql
CREATE TABLE public.mobile_money_reconciliation (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    provider_id         UUID NOT NULL REFERENCES mobile_money_providers(id),
    reconciliation_date DATE NOT NULL,
    -- Statement from provider
    statement_file_path TEXT, -- uploaded provider statement
    statement_total     NUMERIC(19,4),
    statement_count     INT,
    -- System computed
    system_total        NUMERIC(19,4),
    system_count        INT,
    -- Differences
    matched_count       INT NOT NULL DEFAULT 0,
    unmatched_system    INT NOT NULL DEFAULT 0, -- we have it, they don't
    unmatched_provider  INT NOT NULL DEFAULT 0, -- they have it, we don't
    variance_amount     NUMERIC(19,4) DEFAULT 0,
    -- Status
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETED','EXCEPTION')),
    completed_by        UUID REFERENCES users(id),
    completed_at        TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Domain 12 (NEW): Credit Scoring

### credit_score_models
```sql
CREATE TABLE public.credit_score_models (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    model_name      VARCHAR(100) NOT NULL,
    model_version   INT NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    -- Scoring criteria with weights (all configurable by the MFI)
    criteria        JSONB NOT NULL,
    -- Example criteria JSONB:
    -- [
    --   {"code": "REPAYMENT_HISTORY", "label": "Past repayment performance", "weight": 30, "source": "internal"},
    --   {"code": "LOAN_CYCLE", "label": "Number of completed loan cycles", "weight": 15, "source": "internal"},
    --   {"code": "GROUP_MEMBERSHIP", "label": "Group membership tenure (months)", "weight": 10, "source": "internal"},
    --   {"code": "INCOME_STABILITY", "label": "Income source stability", "weight": 15, "source": "manual"},
    --   {"code": "DEBT_TO_INCOME", "label": "Debt-to-income ratio", "weight": 15, "source": "computed"},
    --   {"code": "MOMO_ACTIVITY", "label": "Mobile money transaction volume", "weight": 10, "source": "mobile_money"},
    --   {"code": "BUSINESS_TENURE", "label": "Years in current business", "weight": 5, "source": "manual"}
    -- ]
    score_ranges    JSONB NOT NULL DEFAULT '[
        {"min": 0, "max": 30, "label": "HIGH_RISK", "colour": "red", "recommendation": "DECLINE"},
        {"min": 31, "max": 50, "label": "MEDIUM_RISK", "colour": "amber", "recommendation": "REVIEW"},
        {"min": 51, "max": 70, "label": "ACCEPTABLE", "colour": "yellow", "recommendation": "APPROVE_WITH_CONDITIONS"},
        {"min": 71, "max": 100, "label": "LOW_RISK", "colour": "green", "recommendation": "APPROVE"}
    ]',
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, model_name, model_version)
);
```

### client_credit_scores
```sql
CREATE TABLE public.client_credit_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    client_id           UUID NOT NULL REFERENCES clients(id),
    model_id            UUID NOT NULL REFERENCES credit_score_models(id),
    -- Overall score
    total_score         NUMERIC(5,2) NOT NULL, -- 0-100
    risk_label          VARCHAR(20) NOT NULL, -- HIGH_RISK, MEDIUM_RISK, ACCEPTABLE, LOW_RISK
    recommendation      VARCHAR(30) NOT NULL, -- DECLINE, REVIEW, APPROVE_WITH_CONDITIONS, APPROVE
    -- Component breakdown
    component_scores    JSONB NOT NULL,
    -- Example: [{"code":"REPAYMENT_HISTORY","raw_value":85,"weighted_score":25.5}, ...]
    -- Context
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    computed_for        VARCHAR(20), -- LOAN_APPLICATION, PERIODIC_REVIEW, MANUAL
    loan_id             UUID REFERENCES loans(id), -- if computed for a specific application
    -- Override
    overridden          BOOLEAN NOT NULL DEFAULT FALSE,
    override_score      NUMERIC(5,2),
    override_reason     TEXT,
    overridden_by       UUID REFERENCES users(id),
    overridden_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_credit_scores_client ON client_credit_scores(tenant_id, client_id, computed_at DESC);
CREATE INDEX idx_credit_scores_loan ON client_credit_scores(loan_id) WHERE loan_id IS NOT NULL;
```

---

## Domain 10 (Additions): SMS & USSD

### sms_templates
```sql
CREATE TABLE public.sms_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code    CHAR(2) NOT NULL REFERENCES country_packs(country_code),
    tenant_id       UUID REFERENCES tenants(id), -- NULL = country-wide default
    template_code   VARCHAR(50) NOT NULL,
    -- e.g. REPAYMENT_REMINDER_3DAY, REPAYMENT_REMINDER_DUE,
    -- REPAYMENT_OVERDUE_1DAY, REPAYMENT_OVERDUE_7DAY,
    -- LOAN_APPROVED, LOAN_DISBURSED, BALANCE_INQUIRY_RESPONSE,
    -- KYC_EXPIRY_WARNING, OTP_CODE
    language        CHAR(5) NOT NULL DEFAULT 'en',
    message_body    TEXT NOT NULL,
    -- Placeholders: {{client_name}}, {{amount}}, {{due_date}}, {{loan_number}},
    -- {{balance}}, {{institution_name}}, {{otp_code}}
    max_sms_parts   INT NOT NULL DEFAULT 1, -- cost control: 1 part = 160 chars
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'), country_code, template_code, language)
);
```

### sms_log
```sql
CREATE TABLE public.sms_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    template_id         UUID REFERENCES sms_templates(id),
    recipient_phone     VARCHAR(20) NOT NULL,
    recipient_client_id UUID REFERENCES clients(id),
    recipient_user_id   UUID REFERENCES users(id),
    message_body        TEXT NOT NULL, -- rendered message
    sms_parts           INT NOT NULL DEFAULT 1,
    provider            VARCHAR(30) NOT NULL, -- AFRICAS_TALKING, TWILIO
    provider_message_id VARCHAR(100),
    status              VARCHAR(20) NOT NULL DEFAULT 'QUEUED'
                        CHECK (status IN ('QUEUED','SENT','DELIVERED','FAILED','REJECTED')),
    status_message      TEXT,
    cost_amount         NUMERIC(8,4), -- actual cost charged
    cost_currency       CHAR(3),
    sent_at             TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    triggered_by        VARCHAR(30), -- SCHEDULER, MANUAL, SYSTEM_EVENT, USSD
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sms_status ON sms_log(tenant_id, status, created_at)
    WHERE status IN ('QUEUED','SENT');
```

### ussd_sessions
```sql
CREATE TABLE public.ussd_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id), -- resolved from phone number lookup
    session_id      VARCHAR(100) NOT NULL, -- from Africa's Talking
    phone_number    VARCHAR(20) NOT NULL,
    client_id       UUID REFERENCES clients(id), -- resolved from phone
    service_code    VARCHAR(20) NOT NULL, -- e.g. *384*123#
    current_level   INT NOT NULL DEFAULT 0,
    session_data    JSONB DEFAULT '{}', -- state machine data
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE','COMPLETED','TIMEOUT','ERROR')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    last_input      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Domain 13 (NEW): Report Engine

### report_definitions
```sql
CREATE TABLE public.report_definitions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_code     VARCHAR(50) NOT NULL UNIQUE,
    report_name     VARCHAR(255) NOT NULL,
    description     TEXT,
    category        VARCHAR(30) NOT NULL,
    -- FINANCIAL, PORTFOLIO, REGULATORY, COMPLIANCE, OPERATIONAL, INVESTOR, BOARD
    applicable_roles JSONB NOT NULL DEFAULT '[]', -- which roles can access
    parameters      JSONB NOT NULL DEFAULT '[]',
    -- e.g. [{"name":"date_from","type":"date","required":true},
    --       {"name":"branch_id","type":"uuid","required":false}]
    output_formats  JSONB NOT NULL DEFAULT '["PDF","XLSX","CSV"]',
    template_path   TEXT, -- path to report template file
    query_config    JSONB, -- SQL or view references for data sourcing
    is_system       BOOLEAN NOT NULL DEFAULT TRUE, -- system = cannot delete
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seeded report definitions include:
-- PORTFOLIO_SUMMARY, PAR_AGING, LOAN_BOOK_EXPORT, TRIAL_BALANCE,
-- INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW, CAR_RETURN,
-- LIQUIDITY_RETURN, CLASSIFICATION_OF_ADVANCES, AML_SUMMARY,
-- KYC_STATUS, BOARD_PACK, INVESTOR_REPORT, BRANCH_PERFORMANCE,
-- STAFF_PRODUCTIVITY, COLLECTIONS_REPORT, DISBURSEMENT_REPORT,
-- INSIDER_LENDING_REGISTER, LARGE_EXPOSURE_REPORT
```

### report_schedules
```sql
CREATE TABLE public.report_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    report_id       UUID NOT NULL REFERENCES report_definitions(id),
    schedule_name   VARCHAR(255) NOT NULL,
    frequency       VARCHAR(20) NOT NULL
                    CHECK (frequency IN ('DAILY','WEEKLY','MONTHLY','QUARTERLY','ANNUAL')),
    day_of_week     INT, -- 1=Monday (for WEEKLY)
    day_of_month    INT, -- 1-28 (for MONTHLY/QUARTERLY)
    time_of_day     TIME NOT NULL DEFAULT '06:00:00', -- when to generate
    parameters      JSONB DEFAULT '{}', -- pre-filled parameters
    output_format   VARCHAR(10) NOT NULL DEFAULT 'PDF',
    recipients      JSONB NOT NULL DEFAULT '[]',
    -- [{"user_id":"uuid","delivery":"EMAIL"},{"user_id":"uuid","delivery":"IN_APP"}]
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    next_run_at     TIMESTAMPTZ NOT NULL,
    last_run_at     TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### report_runs
```sql
CREATE TABLE public.report_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    report_id       UUID NOT NULL REFERENCES report_definitions(id),
    schedule_id     UUID REFERENCES report_schedules(id), -- NULL if manual/ad-hoc
    parameters      JSONB NOT NULL DEFAULT '{}',
    output_format   VARCHAR(10) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'QUEUED'
                    CHECK (status IN ('QUEUED','GENERATING','COMPLETED','FAILED')),
    file_path       TEXT, -- Supabase Storage path
    file_size_bytes BIGINT,
    page_count      INT,
    generation_time_ms INT, -- performance tracking
    error_message   TEXT,
    generated_by    UUID REFERENCES users(id), -- NULL if scheduled
    generated_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ, -- auto-cleanup old reports
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_report_runs_recent ON report_runs(tenant_id, created_at DESC);
```

---

## Domain 14 (NEW): Onboarding & Data Import

### onboarding_progress
```sql
CREATE TABLE public.onboarding_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL UNIQUE REFERENCES tenants(id),
    -- Step statuses
    steps           JSONB NOT NULL DEFAULT '[
        {"step": "institution_profile", "label": "Set up institution", "status": "PENDING", "completed_at": null},
        {"step": "upload_logo", "label": "Upload logo & brand colours", "status": "PENDING", "completed_at": null},
        {"step": "country_and_tier", "label": "Select country & licence tier", "status": "PENDING", "completed_at": null},
        {"step": "chart_of_accounts", "label": "Configure chart of accounts", "status": "PENDING", "completed_at": null},
        {"step": "loan_products", "label": "Set up loan products", "status": "PENDING", "completed_at": null},
        {"step": "branches", "label": "Create branches", "status": "PENDING", "completed_at": null},
        {"step": "users_and_roles", "label": "Invite staff & assign roles", "status": "PENDING", "completed_at": null},
        {"step": "first_client", "label": "Register your first client", "status": "PENDING", "completed_at": null},
        {"step": "first_loan", "label": "Create your first loan", "status": "PENDING", "completed_at": null},
        {"step": "maker_checker", "label": "Configure approval workflows", "status": "PENDING", "completed_at": null},
        {"step": "sms_setup", "label": "Set up SMS reminders (optional)", "status": "PENDING", "completed_at": null},
        {"step": "import_data", "label": "Import existing data (optional)", "status": "PENDING", "completed_at": null}
    ]',
    is_complete     BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    skipped_steps   JSONB DEFAULT '[]', -- steps marked as "do later"
    load_demo_data  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### import_jobs
```sql
CREATE TABLE public.import_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    import_type     VARCHAR(30) NOT NULL
                    CHECK (import_type IN (
                        'CLIENTS', 'LOANS', 'REPAYMENT_HISTORY',
                        'CHART_OF_ACCOUNTS', 'OPENING_BALANCES',
                        'DEPOSIT_ACCOUNTS', 'GROUPS'
                    )),
    file_path       TEXT NOT NULL, -- uploaded file in Supabase Storage
    file_name       VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT,
    -- Processing
    status          VARCHAR(20) NOT NULL DEFAULT 'UPLOADED'
                    CHECK (status IN ('UPLOADED','VALIDATING','VALIDATION_COMPLETE',
                        'PREVIEWING','IMPORTING','COMPLETED','FAILED','CANCELLED')),
    total_rows      INT,
    valid_rows      INT,
    error_rows      INT,
    warning_rows    INT,
    -- Validation results
    validation_errors JSONB DEFAULT '[]',
    -- [{"row":5,"field":"national_id_number","error":"Invalid Ghana Card format"},...]
    validation_warnings JSONB DEFAULT '[]',
    -- [{"row":12,"field":"phone","warning":"Duplicate phone number found"},...]
    -- Import results
    imported_count  INT DEFAULT 0,
    skipped_count   INT DEFAULT 0,
    -- Audit
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    approved_by     UUID REFERENCES users(id), -- maker-checker on import
    approved_at     TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Domain 15 (NEW): API Keys & Webhooks

### api_keys
```sql
CREATE TABLE public.api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    key_prefix      VARCHAR(8) NOT NULL, -- visible part: "pk_live_"
    key_hash        VARCHAR(255) NOT NULL, -- hashed full key
    name            VARCHAR(100) NOT NULL, -- "Accounting system integration"
    permissions     JSONB NOT NULL DEFAULT '[]',
    -- ["loan.read","repayment.read","client.read","report.read"]
    rate_limit_per_minute INT NOT NULL DEFAULT 60,
    allowed_ips     JSONB DEFAULT '[]', -- IP whitelist for this key
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ, -- NULL = no expiry
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### webhooks
```sql
CREATE TABLE public.webhooks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    event_type      VARCHAR(50) NOT NULL,
    -- Events: loan.created, loan.approved, loan.disbursed, loan.closed,
    -- repayment.received, repayment.reversed,
    -- client.created, client.kyc_complete,
    -- alert.triggered, alert.escalated,
    -- report.generated, covenant.breached,
    -- momo.success, momo.failed,
    -- sms.delivered, sms.failed
    target_url      TEXT NOT NULL,
    secret_hash     VARCHAR(255) NOT NULL, -- for HMAC signature verification
    headers         JSONB DEFAULT '{}', -- custom headers
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    -- Reliability
    retry_count     INT NOT NULL DEFAULT 3,
    retry_delay_seconds INT NOT NULL DEFAULT 60,
    last_triggered_at TIMESTAMPTZ,
    last_status_code INT,
    consecutive_failures INT NOT NULL DEFAULT 0,
    disabled_at     TIMESTAMPTZ, -- auto-disabled after N failures
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### webhook_deliveries (for debugging)
```sql
CREATE TABLE public.webhook_deliveries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id      UUID NOT NULL REFERENCES webhooks(id),
    event_type      VARCHAR(50) NOT NULL,
    payload         JSONB NOT NULL,
    response_status INT,
    response_body   TEXT,
    response_time_ms INT,
    attempt_number  INT NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING','SUCCESS','FAILED','RETRYING')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-purge deliveries older than 30 days via Celery scheduled task
CREATE INDEX idx_webhook_deliveries_cleanup ON webhook_deliveries(created_at)
    WHERE created_at < now() - interval '30 days';
```

---

## RLS Policies (Applied to All Tables)

```sql
-- Standard tenant isolation policy for every public.* table with tenant_id
-- Applied via Django migration or Supabase SQL editor

ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_{table_name} ON public.{table_name}
    FOR ALL
    USING (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

-- For tables without tenant_id (country_packs, permissions, report_definitions):
-- These are global reference data, readable by all authenticated users
CREATE POLICY read_all_{table_name} ON public.{table_name}
    FOR SELECT
    USING (auth.role() = 'authenticated');
```

---

## Database Triggers (Key Business Rules)

### 1. Deposit block for non-deposit tenants
```sql
CREATE OR REPLACE FUNCTION check_deposit_permission()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM tenants t
        JOIN licence_tiers lt ON t.licence_tier_id = lt.id
        WHERE t.id = NEW.tenant_id AND lt.can_accept_deposits = TRUE
    ) THEN
        RAISE EXCEPTION 'Deposits not permitted under this licence tier';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_deposit_permission
    BEFORE INSERT ON deposit_transactions
    FOR EACH ROW EXECUTE FUNCTION check_deposit_permission();
```

### 2. GL balance check (debits must equal credits per transaction)
```sql
CREATE OR REPLACE FUNCTION check_gl_balance()
RETURNS TRIGGER AS $$
DECLARE
    total_debits NUMERIC(19,4);
    total_credits NUMERIC(19,4);
BEGIN
    SELECT COALESCE(SUM(debit_amount),0), COALESCE(SUM(credit_amount),0)
    INTO total_debits, total_credits
    FROM gl_entries WHERE transaction_id = NEW.transaction_id;

    -- Only check when we have at least 2 entries (a complete transaction)
    IF (SELECT COUNT(*) FROM gl_entries WHERE transaction_id = NEW.transaction_id) >= 2
       AND total_debits != total_credits THEN
        RAISE EXCEPTION 'GL transaction does not balance: debits=% credits=%',
            total_debits, total_credits;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_gl_balance
    AFTER INSERT ON gl_entries
    FOR EACH ROW EXECUTE FUNCTION check_gl_balance();
```

### 3. Maker cannot be checker
```sql
CREATE OR REPLACE FUNCTION check_maker_checker()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.decided_by = (
        SELECT requested_by FROM approval_requests WHERE id = NEW.approval_request_id
    ) THEN
        RAISE EXCEPTION 'Maker-checker violation: approver cannot be the same as requester';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_maker_checker
    BEFORE INSERT ON approval_decisions
    FOR EACH ROW EXECUTE FUNCTION check_maker_checker();
```

### 4. Audit log auto-insert (for key tables)
```sql
CREATE OR REPLACE FUNCTION audit_log_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit.logs (tenant_id, user_id, action, resource_type, resource_id,
                           old_values, new_values, changed_fields)
    VALUES (
        COALESCE(NEW.tenant_id, OLD.tenant_id),
        COALESCE(current_setting('app.current_user_id', true)::uuid, NULL),
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN to_jsonb(NEW) END,
        CASE WHEN TG_OP = 'UPDATE' THEN (
            SELECT jsonb_agg(key) FROM jsonb_each(to_jsonb(NEW))
            WHERE to_jsonb(NEW) -> key != to_jsonb(OLD) -> key
        ) END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Applied to: clients, loans, repayments, deposit_transactions,
-- gl_transactions, aml_alerts, strs, prudential_returns,
-- users, roles, user_roles, maker_checker_configs,
-- licence_profiles, rule_set_versions, investor_profiles, dividends
```

### 5. KYC gate blocks disbursement
```sql
CREATE OR REPLACE FUNCTION check_kyc_before_disbursement()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'DISBURSED' AND OLD.status != 'DISBURSED' THEN
        IF EXISTS (
            SELECT 1 FROM clients c
            WHERE c.id = NEW.client_id AND c.kyc_status = 'INCOMPLETE'
        ) THEN
            RAISE EXCEPTION 'Cannot disburse: client KYC is INCOMPLETE';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_kyc_gate
    BEFORE UPDATE ON loans
    FOR EACH ROW EXECUTE FUNCTION check_kyc_before_disbursement();
```

### 6. Test data block in production
```sql
-- This is enforced at application level via environment variable check,
-- but also add a safety net trigger:
CREATE OR REPLACE FUNCTION block_test_data_in_prod()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_test_data = TRUE
       AND current_setting('app.environment', true) = 'production' THEN
        RAISE EXCEPTION 'Test data cannot be inserted in production environment';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Applied to: clients, loans
```

---

## Indexes Summary (Performance Critical)

```sql
-- High-frequency queries
CREATE INDEX idx_loans_tenant_status ON loans(tenant_id, status);
CREATE INDEX idx_loans_tenant_client ON loans(tenant_id, client_id);
CREATE INDEX idx_loans_tenant_classification ON loans(tenant_id, classification);
CREATE INDEX idx_loans_tenant_officer ON loans(tenant_id, loan_officer_id);
CREATE INDEX idx_loans_overdue ON loans(tenant_id, days_past_due) WHERE days_past_due > 0;

CREATE INDEX idx_repayments_loan ON repayments(tenant_id, loan_id, created_at DESC);
CREATE INDEX idx_repayment_schedules_overdue ON repayment_schedules(loan_id, status)
    WHERE status = 'OVERDUE';

CREATE INDEX idx_clients_tenant_branch ON clients(tenant_id, branch_id);
CREATE INDEX idx_clients_tenant_officer ON clients(tenant_id, assigned_officer_id);
CREATE INDEX idx_clients_kyc_status ON clients(tenant_id, kyc_status)
    WHERE kyc_status != 'VERIFIED';

CREATE INDEX idx_notifications_unread ON notifications(tenant_id, user_id, is_read)
    WHERE is_read = FALSE;

CREATE INDEX idx_aml_alerts_open ON aml_alerts(tenant_id, status)
    WHERE status IN ('OPEN','UNDER_REVIEW','ESCALATED');

-- GL queries
CREATE INDEX idx_gl_entries_account ON gl_entries(tenant_id, account_id);
CREATE INDEX idx_gl_transactions_period ON gl_transactions(tenant_id, period_id);

-- Audit queries (separate schema)
CREATE INDEX idx_audit_tenant_date ON audit.logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit.logs(tenant_id, resource_type, resource_id);
```

---

## Seeded Reference Data (Auto-Created on Platform Deploy)

### Country Packs
- **Ghana** (GH): BoG tiers 1-4, GHS, FIC Ghana, DPA 2012
- **Zambia** (ZM): BoZ tiers I-III, ZMW, FIC Zambia, DPA 2021

### Mobile Money Providers (seeded per country pack)
- GH: MTN_MOMO_GH, VODAFONE_CASH_GH, AIRTELTIGO_GH
- ZM: MTN_MOMO_ZM, AIRTEL_MONEY_ZM, ZOONA_ZM

### SMS Templates (seeded per country, English)
- REPAYMENT_REMINDER_3DAY: "Dear {{client_name}}, your repayment of {{currency}} {{amount}} for loan {{loan_number}} is due on {{due_date}}. Thank you. - {{institution_name}}"
- REPAYMENT_OVERDUE_1DAY: "Dear {{client_name}}, your repayment of {{currency}} {{amount}} was due yesterday. Please make your payment to avoid late charges. - {{institution_name}}"
- LOAN_APPROVED: "Congratulations {{client_name}}! Your loan application {{loan_number}} for {{currency}} {{amount}} has been approved. - {{institution_name}}"
- LOAN_DISBURSED: "Dear {{client_name}}, {{currency}} {{amount}} has been disbursed to your account for loan {{loan_number}}. First repayment due: {{due_date}}. - {{institution_name}}"
- BALANCE_INQUIRY: "{{client_name}}, Loan {{loan_number}}: Outstanding {{currency}} {{balance}}. Next due: {{due_date}} ({{currency}} {{amount}}). - {{institution_name}}"

### System Roles (seeded per tenant)
DATA_ENTRY, LOAN_OFFICER, BRANCH_MANAGER, CREDIT_MANAGER, ACCOUNTANT,
COMPLIANCE_OFFICER, IT_SECURITY_ADMIN, CEO_CFO, BOARD_DIRECTOR,
INVESTOR, EXTERNAL_AUDITOR, INTERNAL_AUDITOR

### Default Report Definitions (20 reports seeded)
See report_definitions table comments above.

### Default Session Configs (per role)
See session_configs table comments above.

### Default Credit Score Model (per country)
Seeded with standard microfinance scoring criteria (configurable by tenant).

---

*Schema Specification v3.0 FINAL — Pan-African Microfinance SaaS Platform*
*57 tables | 6 database triggers | Full RLS | Offline sync*
*Mobile money | Credit scoring | SMS/USSD | Report scheduler*
*Onboarding wizard | Data import | API keys | Webhooks*
*Ready for owner approval → then Django model generation begins*
