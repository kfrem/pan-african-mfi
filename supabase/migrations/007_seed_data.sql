-- ============================================================================
-- Pan-African Microfinance SaaS — Seed Data v3.0
-- Country Packs, Licence Tiers, Rule Sets, MoMo Providers,
-- SMS Templates, Permissions, Report Definitions
-- Run AFTER all migration scripts
-- ============================================================================

-- ======================== COUNTRY PACKS ========================

INSERT INTO country_packs (country_code, country_name, regulatory_authority, default_currency,
    data_protection_law, data_localisation_required, aml_supervisory_body,
    audit_retention_years, default_language, config) VALUES
('GH', 'Ghana', 'Bank of Ghana (BoG)', 'GHS',
    'Data Protection Act, 2012 (Act 843)', TRUE, 'Financial Intelligence Centre (FIC Ghana)',
    7, 'en', '{
        "registration_body": "Data Protection Commission",
        "national_id_format": "GHA-XXXXXXXXX-X",
        "national_id_name": "Ghana Card",
        "interest_cap_exists": false,
        "consumer_protection": "Borrowers & Lenders Act",
        "cooling_off_days": 0,
        "aml_ctr_threshold": 50000,
        "aml_ctr_threshold_currency": "GHS",
        "fiscal_year_start": "01-01",
        "date_format": "DD/MM/YYYY",
        "phone_prefix": "+233",
        "phone_digits": 9
    }'::jsonb),
('ZM', 'Zambia', 'Bank of Zambia (BoZ)', 'ZMW',
    'Data Protection Act, 2021 (Act No. 3 of 2021)', TRUE,
    'Financial Intelligence Centre (FIC Zambia)',
    10, 'en', '{
        "registration_body": "Office of the Data Protection Commissioner",
        "national_id_format": "XXXXXX/XX/X",
        "national_id_name": "National Registration Card (NRC)",
        "interest_cap_exists": true,
        "interest_cap_note": "BoZ national interest rate formula applies",
        "consumer_protection": "Banking and Financial Services Act",
        "cooling_off_days": 0,
        "aml_ctr_threshold": 100000,
        "aml_ctr_threshold_currency": "ZMW",
        "fiscal_year_start": "01-01",
        "date_format": "DD/MM/YYYY",
        "phone_prefix": "+260",
        "phone_digits": 9
    }'::jsonb);

-- ======================== LICENCE TIERS ========================

-- Ghana Tiers
INSERT INTO licence_tiers (country_code, tier_code, tier_name, can_accept_deposits, can_offer_savings,
    can_do_transfers, credit_only, min_capital_amount, min_capital_currency,
    car_requirement_pct, single_obligor_limit_pct, insider_lending_limit_pct,
    reporting_frequency, config) VALUES
('GH', 'GHANA_TIER_1', 'Rural/Community Banks, Finance Houses, S&L', TRUE, TRUE, TRUE, FALSE,
    NULL, 'GHS', 10.00, 25.00, 5.00, 'MONTHLY',
    '{"description": "Tier 1 institutions regulated under Banking Act (Act 673)"}'::jsonb),
('GH', 'GHANA_TIER_2', 'Microfinance Company (Deposit-Taking)', TRUE, TRUE, FALSE, FALSE,
    2000000.0000, 'GHS', 10.00, 10.00, 5.00, 'MONTHLY',
    '{"description": "Deposit-taking MFIs, min capital GHC 2m"}'::jsonb),
('GH', 'GHANA_TIER_3', 'Micro-Credit / Money-Lending Company', FALSE, FALSE, FALSE, TRUE,
    2000000.0000, 'GHS', NULL, 10.00, 5.00, 'MONTHLY',
    '{"description": "Credit-only, cannot raise deposits, min capital GHC 2m", "unsecured_loan_cap_pct": 10.0}'::jsonb),
('GH', 'GHANA_TIER_4', 'Financial NGO / Susu Collector', FALSE, FALSE, FALSE, TRUE,
    NULL, 'GHS', NULL, NULL, NULL, 'QUARTERLY',
    '{"description": "FNGOs and Susu collectors, variable capital requirements"}'::jsonb);

-- Zambia Tiers
INSERT INTO licence_tiers (country_code, tier_code, tier_name, can_accept_deposits, can_offer_savings,
    can_do_transfers, credit_only, min_capital_amount, min_capital_currency,
    car_requirement_pct, single_obligor_limit_pct, insider_lending_limit_pct,
    reporting_frequency, config) VALUES
('ZM', 'ZAMBIA_TIER_I', 'Full MFI (Deposit-Taking)', TRUE, TRUE, TRUE, FALSE,
    NULL, 'ZMW', 10.00, 25.00, 5.00, 'MONTHLY',
    '{"description": "Full microfinance licence under BFSA, deposit-taking"}'::jsonb),
('ZM', 'ZAMBIA_TIER_II', 'Non-Deposit-Taking MFI', FALSE, FALSE, FALSE, TRUE,
    NULL, 'ZMW', NULL, 25.00, 5.00, 'QUARTERLY',
    '{"description": "Non-deposit MFI above capital threshold"}'::jsonb),
('ZM', 'ZAMBIA_TIER_III', 'Small Lender', FALSE, FALSE, FALSE, TRUE,
    NULL, 'ZMW', NULL, NULL, NULL, 'AD_HOC',
    '{"description": "Small lenders, may be outside direct BoZ licence"}'::jsonb);

-- ======================== RULE SET VERSIONS ========================

-- Ghana loan classification rules (BoG)
INSERT INTO rule_set_versions (country_code, rule_type, version_code, version_number,
    effective_from, config) VALUES
('GH', 'LOAN_CLASSIFICATION', 'BOG_LC', 1, '2023-01-01', '{
    "buckets": [
        {"classification": "CURRENT", "min_dpd": 0, "max_dpd": 0, "provision_pct": 1},
        {"classification": "WATCH", "min_dpd": 1, "max_dpd": 30, "provision_pct": 5},
        {"classification": "SUBSTANDARD", "min_dpd": 31, "max_dpd": 90, "provision_pct": 25},
        {"classification": "DOUBTFUL", "min_dpd": 91, "max_dpd": 180, "provision_pct": 50},
        {"classification": "LOSS", "min_dpd": 181, "max_dpd": null, "provision_pct": 100}
    ]
}'::jsonb),
('GH', 'INTEREST_FORMULA', 'BOG_INT', 1, '2022-01-01', '{
    "formula_type": "FLAT_OR_REDUCING",
    "note": "Ghana does not prescribe a national formula; method is product-level choice",
    "max_rate_exists": false
}'::jsonb),
('GH', 'PROVISIONING', 'BOG_PROV', 1, '2023-01-01', '{
    "method": "SPECIFIC_PLUS_GENERAL",
    "general_provision_pct": 1.0,
    "note": "1% general provision on performing portfolio; specific per classification bucket"
}'::jsonb);

-- Zambia loan classification rules (BoZ)
INSERT INTO rule_set_versions (country_code, rule_type, version_code, version_number,
    effective_from, config) VALUES
('ZM', 'LOAN_CLASSIFICATION', 'BOZ_LC', 1, '2023-01-01', '{
    "buckets": [
        {"classification": "CURRENT", "min_dpd": 0, "max_dpd": 0, "provision_pct": 1},
        {"classification": "WATCH", "min_dpd": 1, "max_dpd": 30, "provision_pct": 5},
        {"classification": "SUBSTANDARD", "min_dpd": 31, "max_dpd": 90, "provision_pct": 25},
        {"classification": "DOUBTFUL", "min_dpd": 91, "max_dpd": 180, "provision_pct": 50},
        {"classification": "LOSS", "min_dpd": 181, "max_dpd": null, "provision_pct": 100}
    ]
}'::jsonb),
('ZM', 'INTEREST_FORMULA', 'BOZ_INT', 1, '2022-01-01', '{
    "formula_type": "NATIONAL_PRESCRIBED",
    "note": "BoZ prescribes a national interest rate formula — must be implemented as versioned config",
    "base_rate_source": "BOZ_POLICY_RATE",
    "max_spread_pct": null
}'::jsonb),
('ZM', 'INTEREST_FORMULA', 'BOZ_INT', 2, '2024-07-01', '{
    "formula_type": "NATIONAL_PRESCRIBED",
    "note": "Updated BoZ formula effective July 2024",
    "base_rate_source": "BOZ_POLICY_RATE",
    "max_spread_pct": null,
    "change_circular": "BOZ/MFI/2024/07"
}'::jsonb),
('ZM', 'PROVISIONING', 'BOZ_PROV', 1, '2023-01-01', '{
    "method": "SPECIFIC_PLUS_GENERAL",
    "general_provision_pct": 1.0
}'::jsonb);

-- ======================== MOBILE MONEY PROVIDERS ========================

-- Ghana providers
INSERT INTO mobile_money_providers (country_code, provider_code, provider_name, api_type,
    currency, phone_prefix, phone_regex, api_config) VALUES
('GH', 'MTN_MOMO_GH', 'MTN Mobile Money', 'AFRICAS_TALKING', 'GHS', '+233',
    '^\+233(24|25|53|54|55|59)\d{7}$',
    '{"product_name": "MoMo", "provider": "Athena"}'::jsonb),
('GH', 'VODAFONE_CASH_GH', 'Vodafone Cash', 'AFRICAS_TALKING', 'GHS', '+233',
    '^\+233(20|50)\d{7}$',
    '{"product_name": "VodaCash", "provider": "Athena"}'::jsonb),
('GH', 'AIRTELTIGO_GH', 'AirtelTigo Money', 'AFRICAS_TALKING', 'GHS', '+233',
    '^\+233(26|27|56|57)\d{7}$',
    '{"product_name": "AirtelTigo Money", "provider": "Athena"}'::jsonb);

-- Zambia providers
INSERT INTO mobile_money_providers (country_code, provider_code, provider_name, api_type,
    currency, phone_prefix, phone_regex, api_config) VALUES
('ZM', 'MTN_MOMO_ZM', 'MTN Mobile Money', 'AFRICAS_TALKING', 'ZMW', '+260',
    '^\+260(76|96)\d{7}$',
    '{"product_name": "MoMo", "provider": "Athena"}'::jsonb),
('ZM', 'AIRTEL_MONEY_ZM', 'Airtel Money', 'AFRICAS_TALKING', 'ZMW', '+260',
    '^\+260(77|97)\d{7}$',
    '{"product_name": "Airtel Money", "provider": "Athena"}'::jsonb),
('ZM', 'ZOONA_ZM', 'Zoona', 'DIRECT_API', 'ZMW', '+260', '',
    '{"note": "Direct API integration required"}'::jsonb);

-- ======================== SMS TEMPLATES ========================

-- Ghana SMS templates (English)
INSERT INTO sms_templates (country_code, template_code, language, message_body, max_sms_parts) VALUES
('GH', 'REPAYMENT_REMINDER_3DAY', 'en',
    'Dear {{client_name}}, your repayment of GHS {{amount}} for loan {{loan_number}} is due on {{due_date}}. Thank you. - {{institution_name}}', 1),
('GH', 'REPAYMENT_REMINDER_DUE', 'en',
    'Dear {{client_name}}, your repayment of GHS {{amount}} for loan {{loan_number}} is due TODAY. Please make your payment. - {{institution_name}}', 1),
('GH', 'REPAYMENT_OVERDUE_1DAY', 'en',
    'Dear {{client_name}}, your repayment of GHS {{amount}} was due yesterday. Please pay to avoid late charges. - {{institution_name}}', 1),
('GH', 'REPAYMENT_OVERDUE_7DAY', 'en',
    'URGENT: {{client_name}}, your loan {{loan_number}} is 7 days overdue. Outstanding: GHS {{balance}}. Contact your officer immediately. - {{institution_name}}', 2),
('GH', 'LOAN_APPROVED', 'en',
    'Congratulations {{client_name}}! Your loan {{loan_number}} for GHS {{amount}} has been approved. - {{institution_name}}', 1),
('GH', 'LOAN_DISBURSED', 'en',
    'Dear {{client_name}}, GHS {{amount}} has been sent to your account for loan {{loan_number}}. First payment due: {{due_date}}. - {{institution_name}}', 1),
('GH', 'BALANCE_INQUIRY', 'en',
    '{{client_name}}, Loan {{loan_number}}: Outstanding GHS {{balance}}. Next due: {{due_date}} (GHS {{amount}}). - {{institution_name}}', 1),
('GH', 'REPAYMENT_RECEIVED', 'en',
    'Thank you {{client_name}}! Payment of GHS {{amount}} received for loan {{loan_number}}. New balance: GHS {{balance}}. - {{institution_name}}', 1),
('GH', 'KYC_EXPIRY_WARNING', 'en',
    'Dear {{client_name}}, your ID document expires on {{expiry_date}}. Please visit {{institution_name}} to update your records.', 1);

-- Zambia SMS templates (English)
INSERT INTO sms_templates (country_code, template_code, language, message_body, max_sms_parts) VALUES
('ZM', 'REPAYMENT_REMINDER_3DAY', 'en',
    'Dear {{client_name}}, your repayment of ZMW {{amount}} for loan {{loan_number}} is due on {{due_date}}. Thank you. - {{institution_name}}', 1),
('ZM', 'REPAYMENT_REMINDER_DUE', 'en',
    'Dear {{client_name}}, your repayment of ZMW {{amount}} for loan {{loan_number}} is due TODAY. Please make your payment. - {{institution_name}}', 1),
('ZM', 'REPAYMENT_OVERDUE_1DAY', 'en',
    'Dear {{client_name}}, your repayment of ZMW {{amount}} was due yesterday. Please pay to avoid late charges. - {{institution_name}}', 1),
('ZM', 'REPAYMENT_OVERDUE_7DAY', 'en',
    'URGENT: {{client_name}}, your loan {{loan_number}} is 7 days overdue. Outstanding: ZMW {{balance}}. Contact your officer. - {{institution_name}}', 2),
('ZM', 'LOAN_APPROVED', 'en',
    'Congratulations {{client_name}}! Your loan {{loan_number}} for ZMW {{amount}} has been approved. - {{institution_name}}', 1),
('ZM', 'LOAN_DISBURSED', 'en',
    'Dear {{client_name}}, ZMW {{amount}} has been sent to your account for loan {{loan_number}}. First payment due: {{due_date}}. - {{institution_name}}', 1),
('ZM', 'BALANCE_INQUIRY', 'en',
    '{{client_name}}, Loan {{loan_number}}: Outstanding ZMW {{balance}}. Next due: {{due_date}} (ZMW {{amount}}). - {{institution_name}}', 1),
('ZM', 'REPAYMENT_RECEIVED', 'en',
    'Thank you {{client_name}}! Payment of ZMW {{amount}} received for loan {{loan_number}}. New balance: ZMW {{balance}}. - {{institution_name}}', 1);

-- ======================== PERMISSIONS ========================

INSERT INTO permissions (permission_code, resource, action, description) VALUES
-- Client permissions
('client.create', 'client', 'create', 'Create new clients'),
('client.read', 'client', 'read', 'View client records'),
('client.update', 'client', 'update', 'Edit client records'),
('client.delete', 'client', 'delete', 'Soft-delete clients'),
('client.kyc_verify', 'client', 'kyc_verify', 'Verify KYC documents'),
-- Loan permissions
('loan.create', 'loan', 'create', 'Create loan applications'),
('loan.read', 'loan', 'read', 'View loan records'),
('loan.approve', 'loan', 'approve', 'Approve loan applications'),
('loan.reject', 'loan', 'reject', 'Reject loan applications'),
('loan.disburse', 'loan', 'disburse', 'Disburse approved loans'),
('loan.writeoff', 'loan', 'writeoff', 'Write off loans'),
('loan.restructure', 'loan', 'restructure', 'Restructure loans'),
-- Repayment permissions
('repayment.create', 'repayment', 'create', 'Record repayments'),
('repayment.reverse', 'repayment', 'reverse', 'Reverse repayments'),
-- Deposit permissions
('deposit.create', 'deposit', 'create', 'Create deposit accounts'),
('deposit.transact', 'deposit', 'transact', 'Process deposit transactions'),
-- GL permissions
('gl.post', 'gl', 'post', 'Post journal entries'),
('gl.close_period', 'gl', 'close_period', 'Close accounting periods'),
('gl.view', 'gl', 'view', 'View general ledger'),
-- Report permissions
('report.view', 'report', 'view', 'View dashboards and reports'),
('report.export', 'report', 'export', 'Export reports to PDF/Excel'),
('report.schedule', 'report', 'schedule', 'Schedule automated reports'),
-- Compliance permissions
('compliance.aml_review', 'compliance', 'aml_review', 'Review AML alerts'),
('compliance.str_file', 'compliance', 'str_file', 'File STRs'),
('compliance.prudential_submit', 'compliance', 'prudential_submit', 'Submit prudential returns'),
-- Admin permissions
('admin.user_manage', 'admin', 'user_manage', 'Create/edit/deactivate users'),
('admin.role_manage', 'admin', 'role_manage', 'Manage roles and permissions'),
('admin.tenant_settings', 'admin', 'tenant_settings', 'Modify tenant settings'),
('admin.audit_view', 'admin', 'audit_view', 'View audit logs'),
('admin.session_manage', 'admin', 'session_manage', 'View/terminate sessions'),
('admin.import', 'admin', 'import', 'Import bulk data'),
('admin.api_keys', 'admin', 'api_keys', 'Manage API keys and webhooks'),
-- Investor permissions
('investor.view_portfolio', 'investor', 'view_portfolio', 'View investment portfolio'),
('investor.view_reports', 'investor', 'view_reports', 'View investor reports'),
('investor.share_link', 'investor', 'share_link', 'Create shareable dashboard links'),
-- Board permissions
('board.view_all', 'board', 'view_all', 'View board dashboard'),
('board.insider_register', 'board', 'insider_register', 'View insider lending register'),
('board.board_pack', 'board', 'board_pack', 'Generate board pack'),
-- Mobile money
('momo.initiate', 'momo', 'initiate', 'Initiate mobile money transactions'),
('momo.reconcile', 'momo', 'reconcile', 'Reconcile mobile money statements'),
-- Scoring
('scoring.view', 'scoring', 'view', 'View credit scores'),
('scoring.override', 'scoring', 'override', 'Override credit scores');

-- ======================== REPORT DEFINITIONS ========================

INSERT INTO report_definitions (report_code, report_name, description, category,
    applicable_roles, output_formats) VALUES
('PORTFOLIO_SUMMARY', 'Portfolio Summary', 'Overview of loan portfolio with key metrics', 'PORTFOLIO',
    '["CEO_CFO","BRANCH_MANAGER","CREDIT_MANAGER","INVESTOR","BOARD_DIRECTOR"]', '["PDF","XLSX","CSV"]'),
('PAR_AGING', 'Portfolio at Risk Aging', 'PAR breakdown by aging bucket with trend', 'PORTFOLIO',
    '["CEO_CFO","BRANCH_MANAGER","CREDIT_MANAGER","BOARD_DIRECTOR"]', '["PDF","XLSX"]'),
('LOAN_BOOK_EXPORT', 'Full Loan Book', 'Complete loan-level export for analysis', 'PORTFOLIO',
    '["CEO_CFO","CREDIT_MANAGER","EXTERNAL_AUDITOR","INTERNAL_AUDITOR"]', '["XLSX","CSV"]'),
('TRIAL_BALANCE', 'Trial Balance', 'GL trial balance for selected period', 'FINANCIAL',
    '["ACCOUNTANT","CEO_CFO","EXTERNAL_AUDITOR","INTERNAL_AUDITOR"]', '["PDF","XLSX"]'),
('INCOME_STATEMENT', 'Income Statement', 'Profit & loss for selected period', 'FINANCIAL',
    '["ACCOUNTANT","CEO_CFO","BOARD_DIRECTOR","INVESTOR"]', '["PDF","XLSX"]'),
('BALANCE_SHEET', 'Balance Sheet', 'Statement of financial position', 'FINANCIAL',
    '["ACCOUNTANT","CEO_CFO","BOARD_DIRECTOR","INVESTOR"]', '["PDF","XLSX"]'),
('CASH_FLOW', 'Cash Flow Statement', 'Cash flow for selected period', 'FINANCIAL',
    '["ACCOUNTANT","CEO_CFO","BOARD_DIRECTOR"]', '["PDF","XLSX"]'),
('CAR_RETURN', 'Capital Adequacy Return', 'CAR calculation worksheet', 'REGULATORY',
    '["ACCOUNTANT","COMPLIANCE_OFFICER","CEO_CFO","BOARD_DIRECTOR"]', '["PDF","XLSX"]'),
('LIQUIDITY_RETURN', 'Liquidity Return', 'LCR and NSFR calculation', 'REGULATORY',
    '["ACCOUNTANT","COMPLIANCE_OFFICER","CEO_CFO"]', '["PDF","XLSX"]'),
('CLASSIFICATION_ADVANCES', 'Classification of Advances', 'Loan classification summary per BoG/BoZ', 'REGULATORY',
    '["CREDIT_MANAGER","COMPLIANCE_OFFICER","CEO_CFO","EXTERNAL_AUDITOR"]', '["PDF","XLSX"]'),
('AML_SUMMARY', 'AML Activity Summary', 'AML alerts, STRs filed, and pending actions', 'COMPLIANCE',
    '["COMPLIANCE_OFFICER","CEO_CFO","BOARD_DIRECTOR"]', '["PDF"]'),
('KYC_STATUS', 'KYC Completeness Report', 'Client KYC status overview with gaps', 'COMPLIANCE',
    '["COMPLIANCE_OFFICER","BRANCH_MANAGER"]', '["PDF","XLSX"]'),
('BOARD_PACK', 'Board Pack', 'Full board pack combining all governance metrics', 'BOARD',
    '["BOARD_DIRECTOR","CEO_CFO"]', '["PDF"]'),
('INVESTOR_REPORT', 'Investor Report', 'Periodic investor letter with portfolio metrics', 'INVESTOR',
    '["INVESTOR","CEO_CFO"]', '["PDF"]'),
('BRANCH_PERFORMANCE', 'Branch Performance', 'Branch-level KPIs and staff productivity', 'OPERATIONAL',
    '["BRANCH_MANAGER","CEO_CFO"]', '["PDF","XLSX"]'),
('STAFF_PRODUCTIVITY', 'Staff Productivity', 'Loan officer performance metrics', 'OPERATIONAL',
    '["BRANCH_MANAGER","CEO_CFO"]', '["PDF","XLSX"]'),
('COLLECTIONS_REPORT', 'Collections Report', 'Daily/weekly collections vs targets', 'OPERATIONAL',
    '["BRANCH_MANAGER","LOAN_OFFICER","CEO_CFO"]', '["PDF","XLSX"]'),
('DISBURSEMENT_REPORT', 'Disbursement Report', 'Disbursements by period, product, branch', 'OPERATIONAL',
    '["BRANCH_MANAGER","CREDIT_MANAGER","CEO_CFO"]', '["PDF","XLSX"]'),
('INSIDER_LENDING', 'Insider Lending Register', 'All insider/related-party loan exposures', 'BOARD',
    '["BOARD_DIRECTOR","COMPLIANCE_OFFICER","CEO_CFO","EXTERNAL_AUDITOR"]', '["PDF","XLSX"]'),
('LARGE_EXPOSURE', 'Large Exposure Report', 'Top borrowers as % of capital', 'BOARD',
    '["BOARD_DIRECTOR","CREDIT_MANAGER","CEO_CFO"]', '["PDF","XLSX"]');
