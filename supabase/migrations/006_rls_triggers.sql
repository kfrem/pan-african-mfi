-- ============================================================================
-- Pan-African Microfinance SaaS — Supabase Migration v3.0
-- Part 6: RLS Policies, Database Triggers, Functions
-- ============================================================================

-- ======================== RLS POLICIES ========================
-- Enable RLS on ALL tenant-scoped tables
-- Policy uses JWT claim: auth.jwt() ->> 'tenant_id'

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'tenants', 'licence_profiles', 'branches',
            'users', 'roles', 'user_roles', 'maker_checker_configs',
            'approval_requests', 'approval_decisions',
            'active_sessions', 'session_configs', 'ip_whitelists',
            'clients', 'groups', 'group_members', 'kyc_documents',
            'credit_score_models', 'client_credit_scores',
            'loan_products', 'loans', 'repayment_schedules', 'repayments',
            'deposit_products', 'deposit_accounts', 'deposit_transactions',
            'gl_accounts', 'accounting_periods', 'gl_transactions', 'gl_entries',
            'aml_alerts', 'strs', 'prudential_returns',
            'investor_profiles', 'investor_share_links', 'dividends',
            'mobile_money_transactions', 'mobile_money_reconciliation',
            'notification_rules', 'notifications', 'sms_log', 'ussd_sessions',
            'report_schedules', 'report_runs',
            'onboarding_progress', 'import_jobs',
            'api_keys', 'webhooks', 'webhook_deliveries',
            'sync_queue'
        ])
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
        EXECUTE format(
            'CREATE POLICY tenant_isolation_%I ON public.%I FOR ALL USING (tenant_id = (auth.jwt() ->> ''tenant_id'')::uuid)',
            tbl, tbl
        );
    END LOOP;
END $$;

-- Global reference tables: readable by all authenticated users
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'country_packs', 'licence_tiers', 'rule_set_versions',
            'permissions', 'report_definitions',
            'exchange_rates', 'transaction_monitoring_rules',
            'mobile_money_providers', 'sms_templates'
        ])
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
        EXECUTE format(
            'CREATE POLICY read_all_%I ON public.%I FOR SELECT USING (auth.role() = ''authenticated'')',
            tbl, tbl
        );
    END LOOP;
END $$;

-- Special: group_members inherits access via group's tenant
-- (already covered since group_members links to groups which has RLS)

-- ======================== DATABASE TRIGGERS ========================

-- 1. Deposit permission check (blocks deposits for non-deposit tenants)
CREATE OR REPLACE FUNCTION public.check_deposit_permission()
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_deposit_permission
    BEFORE INSERT ON public.deposit_transactions
    FOR EACH ROW EXECUTE FUNCTION public.check_deposit_permission();

CREATE TRIGGER trg_deposit_account_permission
    BEFORE INSERT ON public.deposit_accounts
    FOR EACH ROW EXECUTE FUNCTION public.check_deposit_permission();

-- 2. GL balance check (debits must equal credits per transaction)
CREATE OR REPLACE FUNCTION public.check_gl_balance()
RETURNS TRIGGER AS $$
DECLARE
    total_debits NUMERIC(19,4);
    total_credits NUMERIC(19,4);
    entry_count INT;
BEGIN
    SELECT COALESCE(SUM(debit_amount),0), COALESCE(SUM(credit_amount),0), COUNT(*)
    INTO total_debits, total_credits, entry_count
    FROM public.gl_entries WHERE transaction_id = NEW.transaction_id;

    IF entry_count >= 2 AND total_debits != total_credits THEN
        RAISE EXCEPTION 'GL transaction does not balance: debits=% credits=%',
            total_debits, total_credits;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_gl_balance
    AFTER INSERT ON public.gl_entries
    FOR EACH ROW EXECUTE FUNCTION public.check_gl_balance();

-- 3. Maker cannot be checker
CREATE OR REPLACE FUNCTION public.check_maker_checker()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.decided_by = (
        SELECT requested_by FROM public.approval_requests WHERE id = NEW.approval_request_id
    ) THEN
        RAISE EXCEPTION 'Maker-checker violation: approver cannot be the same as requester';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_maker_checker
    BEFORE INSERT ON public.approval_decisions
    FOR EACH ROW EXECUTE FUNCTION public.check_maker_checker();

-- 4. KYC gate blocks disbursement
CREATE OR REPLACE FUNCTION public.check_kyc_before_disbursement()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'DISBURSED' AND (OLD.status IS NULL OR OLD.status != 'DISBURSED') THEN
        IF EXISTS (
            SELECT 1 FROM public.clients c
            WHERE c.id = NEW.client_id AND c.kyc_status = 'INCOMPLETE'
        ) THEN
            RAISE EXCEPTION 'Cannot disburse: client KYC is INCOMPLETE';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_kyc_gate
    BEFORE UPDATE ON public.loans
    FOR EACH ROW EXECUTE FUNCTION public.check_kyc_before_disbursement();

-- 5. Test data block in production
CREATE OR REPLACE FUNCTION public.block_test_data_in_prod()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_test_data = TRUE
       AND current_setting('app.environment', true) = 'production' THEN
        RAISE EXCEPTION 'Test data cannot be inserted in production environment';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_test_data_clients
    BEFORE INSERT ON public.clients
    FOR EACH ROW EXECUTE FUNCTION public.block_test_data_in_prod();

CREATE TRIGGER trg_test_data_loans
    BEFORE INSERT ON public.loans
    FOR EACH ROW EXECUTE FUNCTION public.block_test_data_in_prod();

-- 6. Auto-audit log trigger (applied to key tables)
CREATE OR REPLACE FUNCTION public.audit_log_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit.logs (
        tenant_id, user_id, action, resource_type, resource_id,
        old_values, new_values, changed_fields
    )
    VALUES (
        COALESCE(NEW.tenant_id, OLD.tenant_id),
        NULLIF(current_setting('app.current_user_id', true), '')::uuid,
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN to_jsonb(NEW) END,
        CASE WHEN TG_OP = 'UPDATE' THEN (
            SELECT jsonb_agg(key) FROM jsonb_each(to_jsonb(NEW))
            WHERE to_jsonb(NEW) -> key IS DISTINCT FROM to_jsonb(OLD) -> key
        ) END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit trigger to critical tables
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'clients', 'loans', 'repayments', 'deposit_transactions',
            'gl_transactions', 'aml_alerts', 'strs', 'prudential_returns',
            'users', 'roles', 'user_roles', 'maker_checker_configs',
            'licence_profiles', 'rule_set_versions',
            'investor_profiles', 'dividends',
            'mobile_money_transactions'
        ])
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_audit_%I AFTER INSERT OR UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.audit_log_trigger()',
            tbl, tbl
        );
    END LOOP;
END $$;

-- 7. Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT table_name FROM information_schema.columns
        WHERE table_schema = 'public' AND column_name = 'updated_at'
        GROUP BY table_name
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_updated_at_%I BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.update_updated_at()',
            tbl, tbl
        );
    END LOOP;
END $$;
