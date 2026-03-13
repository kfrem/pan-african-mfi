-- ============================================================================
-- Pan-African Microfinance SaaS — Supabase Migration v3.0
-- Part 3: Clients, KYC, Groups, Credit Scoring
-- ============================================================================

-- Clients
CREATE TABLE public.clients (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id           UUID NOT NULL REFERENCES branches(id),
    client_type         VARCHAR(20) NOT NULL CHECK (client_type IN ('INDIVIDUAL','SME','GROUP')),
    client_number       VARCHAR(50) NOT NULL,
    full_legal_name     VARCHAR(255) NOT NULL,
    first_name          VARCHAR(100) DEFAULT '',
    middle_name         VARCHAR(100) DEFAULT '',
    last_name           VARCHAR(100) DEFAULT '',
    date_of_birth       DATE,
    gender              VARCHAR(10) DEFAULT '',
    national_id_type    VARCHAR(50) DEFAULT '',
    national_id_number  VARCHAR(100) DEFAULT '',
    id_issue_date       DATE,
    id_expiry_date      DATE,
    phone_primary       VARCHAR(20) DEFAULT '',
    phone_secondary     VARCHAR(20) DEFAULT '',
    email               VARCHAR(255) DEFAULT '',
    address_line_1      VARCHAR(255) DEFAULT '',
    address_line_2      VARCHAR(255) DEFAULT '',
    city                VARCHAR(100) DEFAULT '',
    region              VARCHAR(100) DEFAULT '',
    country             CHAR(2) DEFAULT '',
    occupation          VARCHAR(100) DEFAULT '',
    employer_name       VARCHAR(255) DEFAULT '',
    monthly_income      NUMERIC(19,4),
    income_currency     CHAR(3) DEFAULT '',
    source_of_funds     VARCHAR(255) DEFAULT '',
    risk_rating         VARCHAR(10) NOT NULL DEFAULT 'LOW'
                        CHECK (risk_rating IN ('LOW','MEDIUM','HIGH')),
    is_pep              BOOLEAN NOT NULL DEFAULT FALSE,
    is_insider          BOOLEAN NOT NULL DEFAULT FALSE,
    insider_relationship VARCHAR(100) DEFAULT '',
    kyc_status          VARCHAR(20) NOT NULL DEFAULT 'INCOMPLETE'
                        CHECK (kyc_status IN ('INCOMPLETE','COMPLETE','VERIFIED','EXPIRED')),
    kyc_verified_by     UUID REFERENCES users(id),
    kyc_verified_at     TIMESTAMPTZ,
    sanctions_checked   BOOLEAN NOT NULL DEFAULT FALSE,
    sanctions_hit       BOOLEAN NOT NULL DEFAULT FALSE,
    onboarding_blocked  BOOLEAN NOT NULL DEFAULT FALSE,
    block_reason        TEXT DEFAULT '',
    assigned_officer_id UUID REFERENCES users(id),
    is_test_data        BOOLEAN NOT NULL DEFAULT FALSE,
    -- Offline sync
    sync_id             UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status         VARCHAR(20) NOT NULL DEFAULT 'SYNCED'
                        CHECK (sync_status IN ('SYNCED','PENDING_UPLOAD','CONFLICT','REJECTED')),
    device_id           VARCHAR(100) DEFAULT '',
    client_created_at   TIMESTAMPTZ,
    client_updated_at   TIMESTAMPTZ,
    server_confirmed_at TIMESTAMPTZ,
    conflict_data       JSONB,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    UNIQUE (tenant_id, client_number)
);

CREATE INDEX idx_clients_national_id ON clients(tenant_id, national_id_number)
    WHERE national_id_number != '';
CREATE INDEX idx_clients_sync ON clients(tenant_id, sync_status)
    WHERE sync_status != 'SYNCED';
CREATE INDEX idx_clients_branch ON clients(tenant_id, branch_id);
CREATE INDEX idx_clients_officer ON clients(tenant_id, assigned_officer_id);
CREATE INDEX idx_clients_kyc ON clients(tenant_id, kyc_status)
    WHERE kyc_status != 'VERIFIED';

-- Groups
CREATE TABLE public.groups (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id           UUID NOT NULL REFERENCES branches(id),
    group_name          VARCHAR(255) NOT NULL,
    group_number        VARCHAR(50) NOT NULL,
    leader_client_id    UUID REFERENCES clients(id),
    meeting_frequency   VARCHAR(20) DEFAULT '',
    meeting_day         VARCHAR(10) DEFAULT '',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    sync_id             UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status         VARCHAR(20) NOT NULL DEFAULT 'SYNCED',
    device_id           VARCHAR(100) DEFAULT '',
    client_created_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, group_number)
);

-- Group Members
CREATE TABLE public.group_members (
    group_id    UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    joined_at   DATE NOT NULL,
    left_at     DATE,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (group_id, client_id)
);

-- KYC Documents
CREATE TABLE public.kyc_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    document_type   VARCHAR(50) NOT NULL,
    file_path       TEXT NOT NULL,
    file_name       VARCHAR(255) DEFAULT '',
    file_size_bytes BIGINT,
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    verified        BOOLEAN NOT NULL DEFAULT FALSE,
    verified_by     UUID REFERENCES users(id),
    verified_at     TIMESTAMPTZ,
    expiry_date     DATE,
    sync_id         UUID NOT NULL DEFAULT gen_random_uuid(),
    sync_status     VARCHAR(20) NOT NULL DEFAULT 'SYNCED',
    device_id       VARCHAR(100) DEFAULT '',
    client_created_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Credit Score Models
CREATE TABLE public.credit_score_models (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    model_name      VARCHAR(100) NOT NULL,
    model_version   INT NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    criteria        JSONB NOT NULL,
    score_ranges    JSONB NOT NULL DEFAULT '[]',
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, model_name, model_version)
);

-- Client Credit Scores
CREATE TABLE public.client_credit_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id           UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    model_id            UUID NOT NULL REFERENCES credit_score_models(id),
    total_score         NUMERIC(5,2) NOT NULL,
    risk_label          VARCHAR(20) NOT NULL,
    recommendation      VARCHAR(30) NOT NULL,
    component_scores    JSONB NOT NULL,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    computed_for        VARCHAR(20) DEFAULT '',
    loan_id             UUID,
    overridden          BOOLEAN NOT NULL DEFAULT FALSE,
    override_score      NUMERIC(5,2),
    override_reason     TEXT DEFAULT '',
    overridden_by       UUID REFERENCES users(id),
    overridden_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_credit_scores_client ON client_credit_scores(tenant_id, client_id, computed_at DESC);
