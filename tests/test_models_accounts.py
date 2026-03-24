"""
Tests for User, Role, Permission, RBAC, and Session models.
Validates every field, constraint, and security behaviour.
"""
import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import (
    User, Role, Permission, RolePermission, UserRole,
    MakerCheckerConfig, ApprovalRequest, ApprovalDecision,
    ActiveSession, SessionConfig, IpWhitelist,
)


pytestmark = pytest.mark.models


class TestUser:
    """User — platform user linked to Supabase auth."""

    def test_all_fields(self, loan_officer_user, tenant, branch):
        u = loan_officer_user
        assert u.tenant == tenant
        assert u.email == 'officer@accramfi.gh'
        assert u.full_name == 'Kwame Mensah'
        assert u.phone == '+233244000001'
        assert u.branch == branch
        assert u.is_active is True
        assert u.is_locked is False
        assert u.failed_login_count == 0
        assert u.mfa_enabled is False
        assert u.language_preference == 'en'
        assert u.theme_preference == 'professional_light'
        assert u.auth_user_id is not None
        assert u.created_at is not None
        assert u.updated_at is not None

    def test_auth_user_id_is_uuid(self, loan_officer_user):
        assert isinstance(loan_officer_user.auth_user_id, uuid.UUID)

    def test_auth_user_id_unique(self, loan_officer_user, tenant, branch, db):
        with pytest.raises(IntegrityError):
            User.objects.create(
                tenant=tenant,
                auth_user_id=loan_officer_user.auth_user_id,  # duplicate
                email='other@accramfi.gh',
                full_name='Other User',
            )

    def test_unique_email_per_tenant(self, loan_officer_user, tenant, db):
        with pytest.raises(IntegrityError):
            User.objects.create(
                tenant=tenant,
                auth_user_id=uuid.uuid4(),
                email='officer@accramfi.gh',  # duplicate in same tenant
                full_name='Duplicate Officer',
            )

    def test_account_lockout_fields(self, locked_user):
        assert locked_user.is_locked is True
        assert locked_user.failed_login_count == 5

    def test_mfa_enabled_for_manager(self, manager_user):
        assert manager_user.mfa_enabled is True

    def test_soft_delete_field(self, loan_officer_user, db):
        assert loan_officer_user.deleted_at is None
        loan_officer_user.deleted_at = timezone.now()
        loan_officer_user.save()
        assert loan_officer_user.is_deleted is True

    def test_is_deleted_property(self, loan_officer_user):
        assert loan_officer_user.is_deleted is False

    def test_password_changed_at_nullable(self, loan_officer_user):
        assert loan_officer_user.password_changed_at is None

    def test_last_login_at_updates(self, loan_officer_user, db):
        now = timezone.now()
        loan_officer_user.last_login_at = now
        loan_officer_user.save()
        loan_officer_user.refresh_from_db()
        assert loan_officer_user.last_login_at is not None

    def test_theme_preferences_stored(self, manager_user):
        assert manager_user.theme_preference == 'professional_dark'

    def test_str_representation(self, loan_officer_user):
        result = str(loan_officer_user)
        assert 'Kwame Mensah' in result
        assert 'officer@accramfi.gh' in result

    def test_branch_assignment_nullable(self, tenant, db):
        u = User.objects.create(
            tenant=tenant,
            auth_user_id=uuid.uuid4(),
            email='noBranch@accramfi.gh',
            full_name='No Branch User',
            branch=None,
        )
        assert u.branch is None


class TestRole:
    """Role — tenant-specific role definitions."""

    def test_all_fields(self, role_loan_officer, tenant):
        r = role_loan_officer
        assert r.tenant == tenant
        assert r.role_code == 'LOAN_OFFICER'
        assert r.role_name == 'Loan Officer'
        assert r.is_system_role is True
        assert 'applications' in r.description.lower()

    def test_unique_together_tenant_role_code(self, role_loan_officer, tenant, db):
        with pytest.raises(IntegrityError):
            Role.objects.create(
                tenant=tenant,
                role_code='LOAN_OFFICER',
                role_name='Duplicate Loan Officer',
            )

    def test_custom_role_not_system(self, tenant, db):
        custom = Role.objects.create(
            tenant=tenant,
            role_code='CUSTOM_REVIEWER',
            role_name='Custom Reviewer',
            is_system_role=False,
            description='Non-system custom role',
        )
        assert custom.is_system_role is False

    def test_str_representation(self, role_loan_officer):
        result = str(role_loan_officer)
        assert 'Loan Officer' in result


class TestPermission:
    """Permission — global permission catalog (resource:action pairs)."""

    def test_all_fields(self, permission_loan_create):
        p = permission_loan_create
        assert p.permission_code == 'LOAN:CREATE'
        assert p.resource == 'LOAN'
        assert p.action == 'CREATE'
        assert 'application' in p.description.lower()

    def test_permission_code_unique(self, permission_loan_create, db):
        with pytest.raises(IntegrityError):
            Permission.objects.create(
                permission_code='LOAN:CREATE',
                resource='LOAN',
                action='CREATE',
            )

    def test_multiple_permissions(self, permission_loan_create, permission_loan_approve, permission_kyc_verify):
        codes = [
            permission_loan_create.permission_code,
            permission_loan_approve.permission_code,
            permission_kyc_verify.permission_code,
        ]
        assert 'LOAN:CREATE' in codes
        assert 'LOAN:APPROVE' in codes
        assert 'CLIENT:VERIFY_KYC' in codes

    def test_str_representation(self, permission_loan_create):
        assert str(permission_loan_create) == 'LOAN:CREATE'


class TestRolePermission:
    """RolePermission — many-to-many: role → permissions."""

    def test_assign_permission_to_role(self, role_loan_officer, permission_loan_create, db):
        rp = RolePermission.objects.create(
            role=role_loan_officer,
            permission=permission_loan_create,
        )
        assert rp.role == role_loan_officer
        assert rp.permission == permission_loan_create

    def test_unique_role_permission(self, role_loan_officer, permission_loan_create, db):
        RolePermission.objects.create(
            role=role_loan_officer,
            permission=permission_loan_create,
        )
        with pytest.raises(IntegrityError):
            RolePermission.objects.create(
                role=role_loan_officer,
                permission=permission_loan_create,
            )

    def test_role_can_have_multiple_permissions(self, role_loan_officer, permission_loan_create, permission_loan_approve, db):
        RolePermission.objects.create(role=role_loan_officer, permission=permission_loan_create)
        RolePermission.objects.create(role=role_loan_officer, permission=permission_loan_approve)
        assert role_loan_officer.role_permissions.count() == 2


class TestUserRole:
    """UserRole — many-to-many: user → roles."""

    def test_assign_role_to_user(self, loan_officer_user, role_loan_officer, db):
        ur = UserRole.objects.create(
            user=loan_officer_user,
            role=role_loan_officer,
        )
        assert ur.user == loan_officer_user
        assert ur.role == role_loan_officer
        assert ur.assigned_at is not None

    def test_user_can_hold_multiple_roles(self, loan_officer_user, role_loan_officer, role_credit_manager, db):
        UserRole.objects.create(user=loan_officer_user, role=role_loan_officer)
        UserRole.objects.create(user=loan_officer_user, role=role_credit_manager)
        assert loan_officer_user.user_roles.count() == 2

    def test_unique_user_role(self, loan_officer_user, role_loan_officer, db):
        UserRole.objects.create(user=loan_officer_user, role=role_loan_officer)
        with pytest.raises(IntegrityError):
            UserRole.objects.create(user=loan_officer_user, role=role_loan_officer)

    def test_assigned_by_nullable(self, loan_officer_user, role_loan_officer, db):
        ur = UserRole.objects.create(
            user=loan_officer_user,
            role=role_loan_officer,
            assigned_by=None,
        )
        assert ur.assigned_by is None


class TestMakerCheckerConfig:
    """MakerCheckerConfig — approval workflow rules per tenant."""

    def test_creation(self, tenant, db):
        config = MakerCheckerConfig.objects.create(
            tenant=tenant,
            action_type='LOAN_APPROVAL',
            min_approvals=2,
            required_roles=['CREDIT_MANAGER', 'BOARD'],
            amount_threshold=None,
            is_active=True,
        )
        assert config.action_type == 'LOAN_APPROVAL'
        assert config.min_approvals == 2
        assert 'CREDIT_MANAGER' in config.required_roles
        assert config.is_active is True

    def test_amount_threshold_decimal(self, tenant, db):
        from decimal import Decimal
        config = MakerCheckerConfig.objects.create(
            tenant=tenant,
            action_type='LARGE_LOAN_APPROVAL',
            min_approvals=3,
            required_roles=['BOARD'],
            amount_threshold=Decimal('100000.00'),
            amount_currency='GHS',
        )
        assert config.amount_threshold == Decimal('100000.0000')
        assert config.amount_currency == 'GHS'

    def test_required_roles_is_json_list(self, tenant, db):
        config = MakerCheckerConfig.objects.create(
            tenant=tenant,
            action_type='WRITE_OFF',
            min_approvals=1,
            required_roles=['BOARD', 'CEO'],
        )
        assert isinstance(config.required_roles, list)


class TestApprovalRequest:
    """ApprovalRequest — maker-checker workflow instance."""

    def test_creation(self, tenant, loan_officer_user, db):
        request = ApprovalRequest.objects.create(
            tenant=tenant,
            action_type='LOAN_DISBURSEMENT',
            target_table='loans',
            target_id=uuid.uuid4(),
            requested_by=loan_officer_user,
            payload={'loan_id': 'abc', 'amount': 5000},
            status='PENDING',
        )
        assert request.status == 'PENDING'
        assert request.action_type == 'LOAN_DISBURSEMENT'
        assert isinstance(request.payload, dict)

    def test_status_choices(self, tenant, loan_officer_user, db):
        for status in ['PENDING', 'APPROVED', 'REJECTED']:
            req = ApprovalRequest.objects.create(
                tenant=tenant,
                action_type=f'ACTION_{status}',
                target_table='loans',
                target_id=uuid.uuid4(),
                requested_by=loan_officer_user,
                payload={},
                status=status,
            )
            assert req.status == status


class TestApprovalDecision:
    """ApprovalDecision — checker sign-off on a request."""

    def test_creation(self, tenant, loan_officer_user, manager_user, db):
        request = ApprovalRequest.objects.create(
            tenant=tenant,
            action_type='LOAN_APPROVAL',
            target_table='loans',
            target_id=uuid.uuid4(),
            requested_by=loan_officer_user,
            payload={},
        )
        decision = ApprovalDecision.objects.create(
            approval_request=request,
            decided_by=manager_user,
            decision='APPROVED',
            comments='Looks good.',
        )
        assert decision.decision == 'APPROVED'
        assert decision.decided_at is not None

    def test_rejected_decision(self, tenant, loan_officer_user, manager_user, db):
        request = ApprovalRequest.objects.create(
            tenant=tenant,
            action_type='WRITE_OFF',
            target_table='loans',
            target_id=uuid.uuid4(),
            requested_by=loan_officer_user,
            payload={},
        )
        decision = ApprovalDecision.objects.create(
            approval_request=request,
            decided_by=manager_user,
            decision='REJECTED',
            comments='Insufficient documentation.',
        )
        assert decision.decision == 'REJECTED'
        assert 'documentation' in decision.comments.lower()


class TestActiveSession:
    """ActiveSession — live user sessions for security monitoring."""

    def test_creation(self, tenant, loan_officer_user, db):
        session = ActiveSession.objects.create(
            tenant=tenant,
            user=loan_officer_user,
            session_token_hash='sha256:abc123def456',
            device_type='MOBILE',
            device_info='Mozilla/5.0 Android',
            ip_address='41.211.100.1',
            location_country='GH',
            location_city='Accra',
            expires_at=timezone.now() + timedelta(hours=8),
            is_active=True,
        )
        assert session.device_type == 'MOBILE'
        assert session.ip_address == '41.211.100.1'
        assert session.is_active is True
        assert session.started_at is not None

    def test_device_type_choices(self, tenant, loan_officer_user, db):
        for device in ['DESKTOP', 'TABLET', 'MOBILE']:
            s = ActiveSession.objects.create(
                tenant=tenant,
                user=loan_officer_user,
                session_token_hash=f'hash_{device}',
                ip_address='127.0.0.1',
                expires_at=timezone.now() + timedelta(hours=1),
                device_type=device,
            )
            assert s.device_type == device

    def test_termination_reasons(self, tenant, loan_officer_user, db):
        for reason in ['LOGOUT', 'TIMEOUT', 'ADMIN_KILL', 'SUSPICIOUS']:
            s = ActiveSession.objects.create(
                tenant=tenant,
                user=loan_officer_user,
                session_token_hash=f'hash_{reason}',
                ip_address='127.0.0.1',
                expires_at=timezone.now() - timedelta(hours=1),
                is_active=False,
                terminated_reason=reason,
            )
            assert s.terminated_reason == reason

    def test_ipv6_address(self, tenant, loan_officer_user, db):
        s = ActiveSession.objects.create(
            tenant=tenant,
            user=loan_officer_user,
            session_token_hash='hash_ipv6',
            ip_address='2a02:2149:8462:1100:c89b:b2f8:a8c6:d07c',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        assert ':' in s.ip_address


class TestSessionConfig:
    """SessionConfig — timeout and security settings per role."""

    def test_creation(self, tenant, db):
        config = SessionConfig.objects.create(
            tenant=tenant,
            role_code='LOAN_OFFICER',
            session_timeout_minutes=480,
            max_concurrent_sessions=3,
            require_ip_whitelist=False,
            require_mfa=False,
        )
        assert config.session_timeout_minutes == 480
        assert config.max_concurrent_sessions == 3
        assert config.require_mfa is False

    def test_compliance_role_requires_mfa(self, tenant, db):
        config = SessionConfig.objects.create(
            tenant=tenant,
            role_code='COMPLIANCE_OFFICER',
            session_timeout_minutes=240,
            max_concurrent_sessions=1,
            require_ip_whitelist=True,
            require_mfa=True,
        )
        assert config.require_mfa is True
        assert config.session_timeout_minutes == 240

    def test_blank_role_code_applies_globally(self, tenant, db):
        """Blank role_code = global default for all roles."""
        config = SessionConfig.objects.create(
            tenant=tenant,
            role_code='',
            session_timeout_minutes=60,
        )
        assert config.role_code == ''


class TestIpWhitelist:
    """IpWhitelist — optional IP restriction per tenant."""

    def test_cidr_notation(self, tenant, loan_officer_user, db):
        entry = IpWhitelist.objects.create(
            tenant=tenant,
            ip_range='192.168.1.0/24',
            description='Office LAN',
            is_active=True,
            created_by=loan_officer_user,
        )
        assert '/' in entry.ip_range  # CIDR notation
        assert entry.is_active is True

    def test_single_ip(self, tenant, loan_officer_user, db):
        entry = IpWhitelist.objects.create(
            tenant=tenant,
            ip_range='41.211.100.5/32',
            description='CEO home IP',
            is_active=True,
            created_by=loan_officer_user,
        )
        assert entry.ip_range.endswith('/32')
