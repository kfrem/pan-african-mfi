-- ============================================================================
-- Pan-African Microfinance SaaS — Supabase Migration v3.0
-- Part 2: Auth, RBAC, Sessions, Maker-Checker
-- ============================================================================

-- Users (extends Supabase auth.users)
CREATE TABLE public.users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id        UUID NOT NULL UNIQUE, -- references auth.users(id)
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email               VARCHAR(255) NOT NULL,
    full_name           VARCHAR(255) NOT NULL,
    phone               VARCHAR(20) DEFAULT '',
    branch_id           UUID REFERENCES branches(id),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_locked           BOOLEAN NOT NULL DEFAULT FALSE,
    failed_login_count  INT NOT NULL DEFAULT 0,
    last_login_at       TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    mfa_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    language_preference CHAR(5) DEFAULT 'en',
    theme_preference    VARCHAR(30) DEFAULT 'professional_light',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    UNIQUE (tenant_id, email)
);

-- Roles
CREATE TABLE public.roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role_code       VARCHAR(50) NOT NULL,
    role_name       VARCHAR(100) NOT NULL,
    is_system_role  BOOLEAN NOT NULL DEFAULT FALSE,
    description     TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, role_code)
);

-- Permissions (global — not tenant-scoped)
CREATE TABLE public.permissions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permission_code     VARCHAR(100) NOT NULL UNIQUE,
    resource            VARCHAR(50) NOT NULL,
    action              VARCHAR(50) NOT NULL,
    description         TEXT DEFAULT ''
);

-- Role-Permission mapping
CREATE TABLE public.role_permissions (
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- User-Role mapping (users can hold multiple roles)
CREATE TABLE public.user_roles (
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    assigned_by     UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Maker-Checker configuration (per tenant)
CREATE TABLE public.maker_checker_configs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    action_type         VARCHAR(100) NOT NULL,
    min_approvals       INT NOT NULL DEFAULT 1,
    required_roles      JSONB NOT NULL DEFAULT '[]',
    amount_threshold    NUMERIC(19,4),
    amount_currency     CHAR(3) DEFAULT '',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, action_type, amount_threshold)
);

-- Approval requests
CREATE TABLE public.approval_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    action_type     VARCHAR(100) NOT NULL,
    target_table    VARCHAR(100) NOT NULL,
    target_id       UUID NOT NULL,
    requested_by    UUID NOT NULL REFERENCES users(id),
    payload         JSONB NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING','APPROVED','REJECTED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);

-- Approval decisions
CREATE TABLE public.approval_decisions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_request_id     UUID NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
    decided_by              UUID NOT NULL REFERENCES users(id),
    decision                VARCHAR(20) NOT NULL CHECK (decision IN ('APPROVED','REJECTED')),
    comments                TEXT DEFAULT '',
    decided_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Active sessions
CREATE TABLE public.active_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash  VARCHAR(255) NOT NULL,
    device_type         VARCHAR(20) DEFAULT '',
    device_info         TEXT DEFAULT '',
    ip_address          INET NOT NULL,
    location_country    CHAR(2) DEFAULT '',
    location_city       VARCHAR(100) DEFAULT '',
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    terminated_by       UUID REFERENCES users(id),
    terminated_reason   VARCHAR(50) DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_active ON active_sessions(tenant_id, user_id, is_active)
    WHERE is_active = TRUE;
CREATE INDEX idx_sessions_ip ON active_sessions(tenant_id, ip_address);

-- Session configs (per tenant, per role)
CREATE TABLE public.session_configs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role_code               VARCHAR(50) DEFAULT '',
    session_timeout_minutes INT NOT NULL DEFAULT 480,
    max_concurrent_sessions INT NOT NULL DEFAULT 3,
    require_ip_whitelist    BOOLEAN NOT NULL DEFAULT FALSE,
    require_mfa             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, role_code)
);

-- IP whitelists
CREATE TABLE public.ip_whitelists (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ip_range    VARCHAR(50) NOT NULL,
    description VARCHAR(255) DEFAULT '',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_by  UUID NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
