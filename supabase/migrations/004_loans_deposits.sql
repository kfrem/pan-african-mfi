-- ============================================================================
-- Pan-African Microfinance SaaS — Supabase Migration v3.0
-- Part 4: Loans, Repayments, Deposits
-- ============================================================================

-- Loan Products
CREATE TABLE public.loan_products (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_code            VARCHAR(20) NOT NULL,
    product_name            VARCHAR(255) NOT NULL,
    product_type            VARCHAR(20) NOT NULL
                            CHECK (product_type IN ('INDIVIDUAL','GROUP','SME','EMERGENCY','AGRICULTURAL')),
    min_amount              NUMERIC(19,4) NOT NULL,
    max_amount              NUMERIC(19,4) NOT NULL,
    min_term_months         INT NOT NULL,
    max_term_months         INT NOT NULL,
    interest_method         VARCHAR(20) NOT NULL CHECK (interest_method IN ('FLAT','REDUCING_BALANCE')),
    default_interest_rate_pct NUMERIC(7,4) NOT NULL,
    origination_fee_pct     NUMERIC(5,2) DEFAULT 0,
    insurance_fee_pct       NUMERIC(5,2) DEFAULT 0,
    requires_collateral     BOOLEAN NOT NULL DEFAULT FALSE,
    requires_guarantor      BOOLEAN NOT NULL DEFAULT FALSE,
    group_liability_type    VARCHAR(20) CHECK (group_liability_type IN ('JOINT','INDIVIDUAL')),
    allowed_frequencies     JSONB NOT NULL DEFAULT '["MONTHLY"]',
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, product_code)
);

-- Loans
CREATE TABLE public.loans (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    loan_number                 VARCHAR(50) NOT NULL,
    client_id                   UUID NOT NULL REFERENCES clients(id),
    group_id                    UUID REFERENCES groups(id),
    product_id                  UUID NOT NULL REFERENCES loan_products(id),
    branch_id                   UUID NOT NULL REFERENCES branches(id),
    loan_officer_id             UUID NOT NULL REFERENCES users(id),
    principal_amount            NUMERIC(19,4) NOT NULL,
    currency                    CHAR(3) NOT NULL,
    interest_rate_pct           NUMERIC(7,4) NOT NULL,
    interest_method             VARCHAR(20) NOT NULL,
    term_months                 INT NOT NULL,
    repayment_frequency         VARCHAR(20) NOT NULL,
    origination_fee             NUMERIC(19,4) DEFAULT 0,
    insurance_fee               NUMERIC(19,4) DEFAULT 0,
    total_interest              NUMERIC(19,4),
    total_repayable             NUMERIC(19,4) NOT NULL,
    outstanding_principal       NUMERIC(19,4) NOT NULL CHECK (outstanding_principal >= 0),
    outstanding_interest        NUMERIC(19,4) NOT NULL DEFAULT 0,
    arrears_amount              NUMERIC(19,4) NOT NULL DEFAULT 0,
    days_past_due               INT NOT NULL DEFAULT 0,
    status                      VARCHAR(20) NOT NULL DEFAULT 'APPLICATION'
                                CHECK (status IN ('APPLICATION','PENDING_APPROVAL','APPROVED',
                                    'DISBURSED','ACTIVE','CLOSED','WRITTEN_OFF','RESTRUCTURED')),
    classification              VARCHAR(20) DEFAULT 'CURRENT'
                                CHECK (classification IN ('CURRENT','WATCH','SUBSTANDARD','DOUBTFUL','LOSS')),
    provision_rate_pct          NUMERIC(5,2) DEFAULT 1.00,
    provision_amount            NUMERIC(19,4) DEFAULT 0,
    application_date            DATE NOT NULL,
    approval_date               DATE,
    disbursement_date           DATE,
    maturity_date               DATE,
    first_repayment_date        DATE,
    closed_date                 DATE,
    approved_by                 UUID REFERENCES users(id),
    disbursed_by                UUID REFERENCES users(id),
    affordability_dti_pct       NUMERIC(5,2),
    collateral_description      TEXT DEFAULT '',
    collateral_value            NUMERIC(19,4),
    guarantor_client_id         UUID REFERENCES clients(id),
    is_insider_loan             BOOLEAN NOT NULL DEFAULT FALSE,
    override_flag               BOOLEAN NOT NULL DEFAULT FALSE,
    override_reason             TEXT DEFAULT '',
    interest_formula_version_id UUID REFERENCES rule_set_versions(id),
    is_test_data                BOOLEAN NOT NULL DEFAULT FALSE,
    -- Offline sync
    sync_id                     UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status                 VARCHAR(20) NOT NULL DEFAULT 'SYNCED',
    device_id                   VARCHAR(100) DEFAULT '',
    client_created_at           TIMESTAMPTZ,
    -- Timestamps
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, loan_number)
);

CREATE INDEX idx_loans_status ON loans(tenant_id, status);
CREATE INDEX idx_loans_client ON loans(tenant_id, client_id);
CREATE INDEX idx_loans_classification ON loans(tenant_id, classification);
CREATE INDEX idx_loans_officer ON loans(tenant_id, loan_officer_id);
CREATE INDEX idx_loans_overdue ON loans(tenant_id, days_past_due) WHERE days_past_due > 0;
CREATE INDEX idx_loans_sync ON loans(tenant_id, sync_status) WHERE sync_status != 'SYNCED';

-- Repayment Schedules
CREATE TABLE public.repayment_schedules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    loan_id             UUID NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    instalment_number   INT NOT NULL,
    due_date            DATE NOT NULL,
    principal_due       NUMERIC(19,4) NOT NULL,
    interest_due        NUMERIC(19,4) NOT NULL,
    fees_due            NUMERIC(19,4) DEFAULT 0,
    total_due           NUMERIC(19,4) NOT NULL,
    principal_paid      NUMERIC(19,4) NOT NULL DEFAULT 0,
    interest_paid       NUMERIC(19,4) NOT NULL DEFAULT 0,
    fees_paid           NUMERIC(19,4) NOT NULL DEFAULT 0,
    total_paid          NUMERIC(19,4) NOT NULL DEFAULT 0,
    balance_after       NUMERIC(19,4),
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING','PAID','PARTIAL','OVERDUE')),
    paid_date           DATE,
    days_late           INT DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (loan_id, instalment_number)
);

CREATE INDEX idx_schedules_overdue ON repayment_schedules(loan_id, status) WHERE status = 'OVERDUE';

-- Repayments (offline-capable)
CREATE TABLE public.repayments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    loan_id             UUID NOT NULL REFERENCES loans(id),
    schedule_id         UUID REFERENCES repayment_schedules(id),
    amount              NUMERIC(19,4) NOT NULL,
    currency            CHAR(3) NOT NULL,
    payment_method      VARCHAR(20) NOT NULL
                        CHECK (payment_method IN ('CASH','MOBILE_MONEY','BANK_TRANSFER','CHEQUE')),
    payment_reference   VARCHAR(100) DEFAULT '',
    received_by         UUID NOT NULL REFERENCES users(id),
    received_at         TIMESTAMPTZ NOT NULL,
    principal_applied   NUMERIC(19,4) NOT NULL,
    interest_applied    NUMERIC(19,4) NOT NULL,
    fees_applied        NUMERIC(19,4) DEFAULT 0,
    penalty_applied     NUMERIC(19,4) DEFAULT 0,
    receipt_number      VARCHAR(50) DEFAULT '',
    reversed            BOOLEAN NOT NULL DEFAULT FALSE,
    reversed_by         UUID REFERENCES users(id),
    reversed_at         TIMESTAMPTZ,
    reversal_reason     TEXT DEFAULT '',
    gl_transaction_id   UUID,
    -- Offline sync
    sync_id             UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status         VARCHAR(20) NOT NULL DEFAULT 'SYNCED',
    device_id           VARCHAR(100) DEFAULT '',
    client_created_at   TIMESTAMPTZ,
    server_confirmed_at TIMESTAMPTZ,
    conflict_data       JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_repayments_loan ON repayments(tenant_id, loan_id, created_at DESC);
CREATE INDEX idx_repayments_sync ON repayments(tenant_id, sync_status) WHERE sync_status != 'SYNCED';

-- ============================================================================
-- DEPOSITS (feature-flagged for deposit-taking tenants only)
-- ============================================================================

-- Deposit Products
CREATE TABLE public.deposit_products (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_code        VARCHAR(20) NOT NULL,
    product_name        VARCHAR(255) NOT NULL,
    product_type        VARCHAR(20) NOT NULL CHECK (product_type IN ('SAVINGS','FIXED_DEPOSIT','CURRENT')),
    interest_rate_pct   NUMERIC(7,4) DEFAULT 0,
    min_balance         NUMERIC(19,4) DEFAULT 0,
    notice_period_days  INT DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, product_code)
);

-- Deposit Accounts
CREATE TABLE public.deposit_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL REFERENCES clients(id),
    product_id      UUID NOT NULL REFERENCES deposit_products(id),
    account_number  VARCHAR(50) NOT NULL,
    currency        CHAR(3) NOT NULL,
    balance         NUMERIC(19,4) NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE','DORMANT','CLOSED')),
    opened_at       DATE NOT NULL,
    closed_at       DATE,
    maturity_date   DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, account_number)
);

-- Deposit Transactions
CREATE TABLE public.deposit_transactions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    account_id          UUID NOT NULL REFERENCES deposit_accounts(id),
    transaction_type    VARCHAR(20) NOT NULL
                        CHECK (transaction_type IN ('DEPOSIT','WITHDRAWAL','INTEREST_CREDIT','FEE_DEBIT','TRANSFER')),
    amount              NUMERIC(19,4) NOT NULL,
    balance_after       NUMERIC(19,4) NOT NULL,
    description         TEXT DEFAULT '',
    payment_method      VARCHAR(20) DEFAULT '',
    reference           VARCHAR(100) DEFAULT '',
    performed_by        UUID NOT NULL REFERENCES users(id),
    gl_transaction_id   UUID,
    sync_id             UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status         VARCHAR(20) NOT NULL DEFAULT 'SYNCED',
    device_id           VARCHAR(100) DEFAULT '',
    client_created_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
