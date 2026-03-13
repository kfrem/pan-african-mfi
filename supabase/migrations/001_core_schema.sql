-- ============================================================================
-- Pan-African Microfinance SaaS — Supabase Migration v3.0
-- Part 1: Schemas, Extensions, Core Tables (Tenants & Config)
-- Run this FIRST in Supabase SQL Editor
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Audit schema (append-only — app role gets INSERT + SELECT only)
CREATE SCHEMA IF NOT EXISTS audit;

-- ============================================================================
-- DOMAIN 1: TENANTS & CONFIGURATION
-- ============================================================================

-- Country Packs (global reference — not tenant-scoped)
CREATE TABLE public.country_packs (
    country_code            CHAR(2) PRIMARY KEY,
    country_name            VARCHAR(100) NOT NULL,
    regulatory_authority    VARCHAR(255) NOT NULL,
    default_currency        CHAR(3) NOT NULL,
    data_protection_law     VARCHAR(255) DEFAULT '',
    data_localisation_required BOOLEAN NOT NULL DEFAULT FALSE,
    aml_supervisory_body    VARCHAR(255) DEFAULT '',
    audit_retention_years   INT NOT NULL DEFAULT 7,
    default_language        CHAR(5) NOT NULL DEFAULT 'en',
    config                  JSONB NOT NULL DEFAULT '{}',
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Licence Tiers
CREATE TABLE public.licence_tiers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code            CHAR(2) NOT NULL REFERENCES country_packs(country_code),
    tier_code               VARCHAR(50) NOT NULL,
    tier_name               VARCHAR(255) NOT NULL,
    can_accept_deposits     BOOLEAN NOT NULL DEFAULT FALSE,
    can_offer_savings       BOOLEAN NOT NULL DEFAULT FALSE,
    can_do_transfers        BOOLEAN NOT NULL DEFAULT FALSE,
    credit_only             BOOLEAN NOT NULL DEFAULT FALSE,
    min_capital_amount      NUMERIC(19,4),
    min_capital_currency    CHAR(3),
    car_requirement_pct     NUMERIC(5,2),
    single_obligor_limit_pct NUMERIC(5,2),
    insider_lending_limit_pct NUMERIC(5,2),
    reporting_frequency     VARCHAR(20) NOT NULL DEFAULT 'MONTHLY'
                            CHECK (reporting_frequency IN ('MONTHLY','QUARTERLY','AD_HOC')),
    config                  JSONB DEFAULT '{}',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (country_code, tier_code)
);

-- Tenants (root entity)
CREATE TABLE public.tenants (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(255) NOT NULL,
    trading_name            VARCHAR(255) DEFAULT '',
    country_code            CHAR(2) NOT NULL REFERENCES country_packs(country_code),
    licence_tier_id         UUID NOT NULL REFERENCES licence_tiers(id),
    status                  VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                            CHECK (status IN ('ACTIVE','SUSPENDED','TERMINATED')),
    subscription_active     BOOLEAN NOT NULL DEFAULT TRUE,
    default_currency        CHAR(3) NOT NULL,
    default_language        CHAR(5) NOT NULL DEFAULT 'en',
    timezone                VARCHAR(50) NOT NULL DEFAULT 'UTC',
    logo_url                TEXT DEFAULT '',
    primary_brand_colour    CHAR(7) DEFAULT '',
    secondary_brand_colour  CHAR(7) DEFAULT '',
    custom_domain           VARCHAR(255) UNIQUE,
    tagline                 VARCHAR(255) DEFAULT '',
    data_localisation_required BOOLEAN NOT NULL DEFAULT FALSE,
    data_centre_tag         VARCHAR(50) DEFAULT '',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rule Set Versions (versioned regulatory rules)
CREATE TABLE public.rule_set_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code        CHAR(2) NOT NULL REFERENCES country_packs(country_code),
    rule_type           VARCHAR(50) NOT NULL
                        CHECK (rule_type IN ('INTEREST_FORMULA','LOAN_CLASSIFICATION','PROVISIONING')),
    version_code        VARCHAR(50) NOT NULL,
    version_number      INT NOT NULL,
    effective_from      DATE NOT NULL,
    effective_to        DATE,
    config              JSONB NOT NULL,
    approved_by         UUID,
    approved_at         TIMESTAMPTZ,
    change_justification TEXT DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (country_code, rule_type, version_code, version_number)
);

-- Licence Profiles (one per tenant)
CREATE TABLE public.licence_profiles (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    licence_number              VARCHAR(100) DEFAULT '',
    licensing_authority         VARCHAR(255) DEFAULT '',
    effective_from              DATE,
    expires_on                  DATE,
    permitted_features          JSONB NOT NULL DEFAULT '{}',
    active_interest_formula_id  UUID REFERENCES rule_set_versions(id),
    active_classification_id    UUID REFERENCES rule_set_versions(id),
    active_provisioning_id      UUID REFERENCES rule_set_versions(id),
    aml_supervisory_body        VARCHAR(255) DEFAULT '',
    str_required                BOOLEAN NOT NULL DEFAULT TRUE,
    kyc_minimum_level           VARCHAR(20) NOT NULL DEFAULT 'FULL_CDD',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Branches
CREATE TABLE public.branches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_code     VARCHAR(20) NOT NULL,
    branch_name     VARCHAR(255) NOT NULL,
    branch_type     VARCHAR(20) CHECK (branch_type IN ('URBAN','PERI_URBAN','RURAL')),
    address         TEXT DEFAULT '',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, branch_code)
);
