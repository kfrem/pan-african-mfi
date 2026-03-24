"""
Tests for Tenant, CountryPack, LicenceTier, Branch, RuleSetVersion models.
Validates every field, constraint, and choice value.
"""
import pytest
from datetime import date
from decimal import Decimal

from django.db import IntegrityError

from apps.tenants.models import CountryPack, LicenceTier, Tenant, Branch, RuleSetVersion, LicenceProfile


pytestmark = pytest.mark.models


class TestCountryPack:
    """CountryPack — regulatory reference data per country."""

    def test_creation_with_all_fields(self, country_gh):
        assert country_gh.country_code == 'GH'
        assert country_gh.country_name == 'Ghana'
        assert country_gh.regulatory_authority == 'Bank of Ghana'
        assert country_gh.default_currency == 'GHS'
        assert country_gh.data_protection_law == 'Data Protection Act 2012'
        assert country_gh.data_localisation_required is False
        assert country_gh.aml_supervisory_body == 'Financial Intelligence Centre'
        assert country_gh.audit_retention_years == 7
        assert country_gh.default_language == 'en'
        assert country_gh.is_active is True
        assert isinstance(country_gh.config, dict)
        assert country_gh.created_at is not None
        assert country_gh.updated_at is not None

    def test_primary_key_is_country_code(self, country_gh):
        assert country_gh.pk == 'GH'

    def test_country_code_uniqueness(self, country_gh, db):
        with pytest.raises(IntegrityError):
            CountryPack.objects.create(
                country_code='GH',
                country_name='Another Ghana',
                regulatory_authority='Test',
                default_currency='GHS',
            )

    def test_config_json_structure(self, country_gh):
        rules = country_gh.config.get('classification_rules', {})
        assert 'CURRENT' in rules
        assert 'WATCH' in rules
        assert 'LOSS' in rules
        assert rules['LOSS']['provision_pct'] == 100

    def test_second_country_zambia(self, country_zm):
        assert country_zm.country_code == 'ZM'
        assert country_zm.default_currency == 'ZMW'

    def test_str_representation(self, country_gh):
        assert 'Ghana' in str(country_gh)
        assert 'GH' in str(country_gh)

    def test_inactive_country_pack(self, db):
        pack = CountryPack.objects.create(
            country_code='NG',
            country_name='Nigeria',
            regulatory_authority='CBN',
            default_currency='NGN',
            is_active=False,
        )
        assert pack.is_active is False

    def test_data_retention_field(self, country_gh):
        """Financial institutions must retain audit data — minimum 7 years."""
        assert country_gh.audit_retention_years >= 7


class TestLicenceTier:
    """LicenceTier — feature flags and regulatory thresholds per tier."""

    def test_tier_2_all_fields(self, licence_tier, country_gh):
        assert licence_tier.country == country_gh
        assert licence_tier.tier_code == 'TIER_2'
        assert licence_tier.tier_name == 'Tier 2 MFI'
        assert licence_tier.can_accept_deposits is True
        assert licence_tier.can_offer_savings is True
        assert licence_tier.can_do_transfers is True
        assert licence_tier.credit_only is False
        assert licence_tier.min_capital_amount == Decimal('500000.00')
        assert licence_tier.min_capital_currency == 'GHS'
        assert licence_tier.car_requirement_pct == Decimal('10.00')
        assert licence_tier.single_obligor_limit_pct == Decimal('15.00')
        assert licence_tier.insider_lending_limit_pct == Decimal('10.00')
        assert licence_tier.reporting_frequency == 'MONTHLY'

    def test_credit_only_tier_feature_flags(self, credit_only_tier):
        assert credit_only_tier.credit_only is True
        assert credit_only_tier.can_accept_deposits is False
        assert credit_only_tier.can_offer_savings is False
        assert credit_only_tier.can_do_transfers is False

    def test_unique_together_country_tier_code(self, licence_tier, country_gh):
        with pytest.raises(IntegrityError):
            LicenceTier.objects.create(
                country=country_gh,
                tier_code='TIER_2',
                tier_name='Duplicate Tier',
                reporting_frequency='MONTHLY',
            )

    def test_reporting_frequency_choices(self, db, country_gh):
        for freq in ['MONTHLY', 'QUARTERLY', 'AD_HOC']:
            tier = LicenceTier.objects.create(
                country=country_gh,
                tier_code=f'TEST_{freq}',
                tier_name=f'Test {freq}',
                reporting_frequency=freq,
            )
            assert tier.reporting_frequency == freq

    def test_capital_requirement_precision(self, licence_tier):
        """Min capital must be stored with 4 decimal precision."""
        assert licence_tier.min_capital_amount == Decimal('500000.0000')

    def test_str_representation(self, licence_tier):
        result = str(licence_tier)
        assert 'GH' in result or 'Tier 2' in result

    def test_uuid_primary_key(self, licence_tier):
        import uuid
        assert isinstance(licence_tier.id, uuid.UUID)


class TestTenant:
    """Tenant — root entity per MFI institution."""

    def test_all_fields(self, tenant, country_gh, licence_tier):
        assert tenant.name == 'Accra MFI Ltd'
        assert tenant.trading_name == 'AccraMFI'
        assert tenant.country == country_gh
        assert tenant.licence_tier == licence_tier
        assert tenant.status == 'ACTIVE'
        assert tenant.subscription_active is True
        assert tenant.default_currency == 'GHS'
        assert tenant.default_language == 'en'
        assert tenant.timezone == 'Africa/Accra'
        assert tenant.primary_brand_colour == '#004080'
        assert tenant.secondary_brand_colour == '#FFD700'
        assert tenant.tagline == 'Banking the unbanked'
        assert tenant.data_localisation_required is False
        assert tenant.created_at is not None
        assert tenant.updated_at is not None

    def test_status_choices(self, tenant, db, country_gh, licence_tier):
        for status in ['ACTIVE', 'SUSPENDED', 'TERMINATED']:
            tenant.status = status
            tenant.save()
            tenant.refresh_from_db()
            assert tenant.status == status

    def test_custom_domain_unique(self, tenant, db, country_gh, licence_tier):
        tenant.custom_domain = 'accramfi.gh'
        tenant.save()
        with pytest.raises(IntegrityError):
            Tenant.objects.create(
                name='Other MFI',
                country=country_gh,
                licence_tier=licence_tier,
                status='ACTIVE',
                default_currency='GHS',
                custom_domain='accramfi.gh',
            )

    def test_null_custom_domain_allowed(self, tenant):
        assert tenant.custom_domain is None

    def test_str_returns_trading_name(self, tenant):
        assert str(tenant) == 'AccraMFI'

    def test_str_falls_back_to_name(self, db, country_gh, licence_tier):
        t = Tenant.objects.create(
            name='NoTradingName MFI',
            country=country_gh,
            licence_tier=licence_tier,
            default_currency='GHS',
        )
        assert str(t) == 'NoTradingName MFI'

    def test_uuid_primary_key(self, tenant):
        import uuid
        assert isinstance(tenant.id, uuid.UUID)

    def test_brand_colour_format(self, tenant):
        """Hex colours must be 7 chars (#RRGGBB)."""
        assert len(tenant.primary_brand_colour) == 7
        assert tenant.primary_brand_colour.startswith('#')
        assert len(tenant.secondary_brand_colour) == 7

    def test_multiple_tenants_independent(self, tenant, country_gh, licence_tier, db):
        tenant2 = Tenant.objects.create(
            name='Kumasi MFI Ltd',
            trading_name='KumasiMFI',
            country=country_gh,
            licence_tier=licence_tier,
            status='ACTIVE',
            default_currency='GHS',
        )
        assert tenant.id != tenant2.id
        assert Tenant.objects.count() == 2


class TestBranch:
    """Branch — physical/logical location per tenant."""

    def test_all_fields(self, branch, tenant):
        assert branch.tenant == tenant
        assert branch.branch_code == 'HQ'
        assert branch.branch_name == 'Head Office'
        assert branch.branch_type == 'URBAN'
        assert branch.address == '1 Liberation Road, Accra'
        assert branch.is_active is True

    def test_branch_type_choices(self, tenant, db):
        for btype in ['URBAN', 'PERI_URBAN', 'RURAL']:
            b = Branch.objects.create(
                tenant=tenant,
                branch_code=f'TEST-{btype}',
                branch_name=f'{btype} Branch',
                branch_type=btype,
                is_active=True,
            )
            assert b.branch_type == btype

    def test_unique_together_tenant_code(self, branch, tenant):
        with pytest.raises(IntegrityError):
            Branch.objects.create(
                tenant=tenant,
                branch_code='HQ',
                branch_name='Duplicate HQ',
                is_active=True,
            )

    def test_different_tenants_can_share_branch_code(self, db, branch, country_gh, licence_tier):
        tenant2 = Tenant.objects.create(
            name='Other MFI',
            country=country_gh,
            licence_tier=licence_tier,
            default_currency='GHS',
        )
        Branch.objects.create(
            tenant=tenant2,
            branch_code='HQ',  # Same code, different tenant — OK
            branch_name='Other HQ',
            is_active=True,
        )
        assert Branch.objects.filter(branch_code='HQ').count() == 2

    def test_rural_branch(self, rural_branch):
        assert rural_branch.branch_type == 'RURAL'

    def test_str_representation(self, branch):
        result = str(branch)
        assert 'Head Office' in result or 'HQ' in result


class TestRuleSetVersion:
    """RuleSetVersion — versioned regulatory rules (classification, provisioning)."""

    def test_all_fields(self, rule_set_version, country_gh):
        assert rule_set_version.country == country_gh
        assert rule_set_version.rule_type == 'LOAN_CLASSIFICATION'
        assert rule_set_version.version_code == 'BOG-2024'
        assert rule_set_version.version_number == 1
        assert rule_set_version.effective_from == date(2024, 1, 1)
        assert rule_set_version.effective_to is None
        assert isinstance(rule_set_version.config, dict)

    def test_rule_type_choices(self, country_gh, db):
        for rtype in ['INTEREST_FORMULA', 'LOAN_CLASSIFICATION', 'PROVISIONING']:
            rv = RuleSetVersion.objects.create(
                country=country_gh,
                rule_type=rtype,
                version_code=f'TEST-{rtype}',
                version_number=1,
                effective_from=date(2024, 1, 1),
                config={},
            )
            assert rv.rule_type == rtype

    def test_config_stores_classification_bands(self, rule_set_version):
        config = rule_set_version.config
        assert 'CURRENT' in config
        assert 'LOSS' in config
        assert config['LOSS']['provision_pct'] == 100

    def test_unique_together_constraint(self, rule_set_version, country_gh, db):
        with pytest.raises(IntegrityError):
            RuleSetVersion.objects.create(
                country=country_gh,
                rule_type='LOAN_CLASSIFICATION',
                version_code='BOG-2024',
                version_number=1,
                effective_from=date(2024, 1, 1),
                config={},
            )

    def test_versioning_increments(self, rule_set_version, country_gh, db):
        v2 = RuleSetVersion.objects.create(
            country=country_gh,
            rule_type='LOAN_CLASSIFICATION',
            version_code='BOG-2025',
            version_number=2,
            effective_from=date(2025, 1, 1),
            config={'CURRENT': {'days': 30}},
        )
        assert v2.version_number == 2
        assert v2.version_code != rule_set_version.version_code


class TestLicenceProfile:
    """LicenceProfile — per-tenant licence identity."""

    def test_creation(self, tenant, rule_set_version, db):
        profile = LicenceProfile.objects.create(
            tenant=tenant,
            licence_number='BOG/MFI/2024/001',
            licensing_authority='Bank of Ghana',
            effective_from=date(2024, 1, 1),
            expires_on=date(2026, 12, 31),
            permitted_features={'loans': True, 'deposits': True},
            active_classification=rule_set_version,
            str_required=True,
            kyc_minimum_level='FULL_CDD',
        )
        assert profile.tenant == tenant
        assert profile.licence_number == 'BOG/MFI/2024/001'
        assert profile.str_required is True
        assert profile.kyc_minimum_level == 'FULL_CDD'

    def test_one_to_one_uniqueness(self, tenant, db):
        LicenceProfile.objects.create(
            tenant=tenant,
            licence_number='BOG/001',
            licensing_authority='BoG',
        )
        with pytest.raises(IntegrityError):
            LicenceProfile.objects.create(
                tenant=tenant,
                licence_number='BOG/002',
                licensing_authority='BoG',
            )

    def test_kyc_minimum_level_default(self, tenant, db):
        profile = LicenceProfile.objects.create(
            tenant=tenant,
            licence_number='BOG/003',
        )
        assert profile.kyc_minimum_level == 'FULL_CDD'

    def test_str_required_default(self, tenant, db):
        profile = LicenceProfile.objects.create(
            tenant=tenant,
            licence_number='BOG/004',
        )
        assert profile.str_required is True
