"""
Tests for Client, Group, GroupMember, KycDocument models.
Tests every field including KYC, PEP, insider, and sanctions flags.
"""
import uuid
from datetime import date, timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.clients.models import Client, Group, GroupMember, KycDocument


pytestmark = pytest.mark.models


class TestClient:
    """Client — core customer record with KYC and compliance fields."""

    def test_individual_client_all_fields(self, individual_client, tenant, branch, loan_officer_user):
        c = individual_client
        assert c.tenant == tenant
        assert c.branch == branch
        assert c.client_type == 'INDIVIDUAL'
        assert c.client_number == 'CLT-2024-00001'
        assert c.full_legal_name == 'Kofi Boateng'
        assert c.first_name == 'Kofi'
        assert c.last_name == 'Boateng'
        assert c.date_of_birth == date(1985, 6, 15)
        assert c.gender == 'MALE'
        assert c.national_id_type == 'GHANA_CARD'
        assert c.national_id_number == 'GHA-123456789-0'
        assert c.id_issue_date == date(2020, 1, 1)
        assert c.id_expiry_date == date(2030, 1, 1)
        assert c.phone_primary == '+233244100001'
        assert c.phone_secondary == '+233244100002'
        assert c.email == 'kofi.boateng@email.com'
        assert c.address_line_1 == '24 Tema Road'
        assert c.city == 'Accra'
        assert c.region == 'Greater Accra'
        assert c.country == 'GH'
        assert c.occupation == 'Trader'
        assert c.monthly_income is not None
        assert c.income_currency == 'GHS'
        assert c.source_of_funds == 'Business income'
        assert c.risk_rating == 'LOW'
        assert c.is_pep is False
        assert c.is_insider is False
        assert c.kyc_status == 'COMPLETE'
        assert c.sanctions_checked is True
        assert c.sanctions_hit is False
        assert c.onboarding_blocked is False
        assert c.assigned_officer == loan_officer_user
        assert c.created_at is not None
        assert c.updated_at is not None

    def test_sme_client_type(self, sme_client):
        assert sme_client.client_type == 'SME'
        assert sme_client.full_legal_name == 'Accra Traders Ltd'

    def test_gender_choices(self, tenant, branch, loan_officer_user, db):
        for gender in ['MALE', 'FEMALE', 'OTHER']:
            c = Client.objects.create(
                tenant=tenant,
                branch=branch,
                client_type='INDIVIDUAL',
                client_number=f'CLT-TEST-{gender}',
                full_legal_name=f'{gender} Person',
                gender=gender,
                kyc_status='INCOMPLETE',
                risk_rating='LOW',
                assigned_officer=loan_officer_user,
            )
            assert c.gender == gender

    def test_client_type_choices(self, tenant, branch, loan_officer_user, db):
        for ctype in ['INDIVIDUAL', 'SME', 'GROUP']:
            c = Client.objects.create(
                tenant=tenant,
                branch=branch,
                client_type=ctype,
                client_number=f'CLT-TYPE-{ctype}',
                full_legal_name=f'{ctype} Client',
                kyc_status='INCOMPLETE',
                risk_rating='LOW',
                assigned_officer=loan_officer_user,
            )
            assert c.client_type == ctype

    def test_kyc_status_choices(self, tenant, branch, loan_officer_user, db):
        for status in ['INCOMPLETE', 'COMPLETE', 'VERIFIED', 'EXPIRED']:
            c = Client.objects.create(
                tenant=tenant,
                branch=branch,
                client_type='INDIVIDUAL',
                client_number=f'CLT-KYC-{status}',
                full_legal_name=f'KYC {status} Client',
                kyc_status=status,
                risk_rating='LOW',
                assigned_officer=loan_officer_user,
            )
            assert c.kyc_status == status

    def test_risk_rating_choices(self, tenant, branch, loan_officer_user, db):
        for rating in ['LOW', 'MEDIUM', 'HIGH']:
            c = Client.objects.create(
                tenant=tenant,
                branch=branch,
                client_type='INDIVIDUAL',
                client_number=f'CLT-RISK-{rating}',
                full_legal_name=f'{rating} Risk Client',
                kyc_status='INCOMPLETE',
                risk_rating=rating,
                assigned_officer=loan_officer_user,
            )
            assert c.risk_rating == rating

    def test_pep_client_fields(self, pep_client):
        assert pep_client.is_pep is True
        assert pep_client.risk_rating == 'HIGH'

    def test_insider_client_fields(self, insider_client):
        assert insider_client.is_insider is True
        assert insider_client.insider_relationship == 'Spouse of Director'

    def test_sanctions_hit_blocks_onboarding(self, blocked_client):
        assert blocked_client.sanctions_hit is True
        assert blocked_client.onboarding_blocked is True
        assert 'OFAC' in blocked_client.block_reason or 'Sanctions' in blocked_client.block_reason

    def test_unique_client_number_per_tenant(self, individual_client, tenant, branch, loan_officer_user, db):
        with pytest.raises(IntegrityError):
            Client.objects.create(
                tenant=tenant,
                branch=branch,
                client_type='INDIVIDUAL',
                client_number='CLT-2024-00001',  # duplicate
                full_legal_name='Duplicate Client',
                kyc_status='INCOMPLETE',
                risk_rating='LOW',
                assigned_officer=loan_officer_user,
            )

    def test_soft_delete_field(self, individual_client, db):
        assert individual_client.deleted_at is None
        individual_client.deleted_at = timezone.now()
        individual_client.save()
        assert individual_client.is_deleted is True

    def test_uuid_primary_key(self, individual_client):
        assert isinstance(individual_client.id, uuid.UUID)

    def test_income_decimal_precision(self, individual_client):
        from decimal import Decimal
        assert individual_client.monthly_income == Decimal('2500.00')

    def test_verified_kyc_sets_verifier(self, verified_client, manager_user):
        assert verified_client.kyc_status == 'VERIFIED'
        assert verified_client.kyc_verified_by == manager_user
        assert verified_client.kyc_verified_at is not None

    def test_is_test_data_flag(self, tenant, branch, loan_officer_user, db):
        c = Client.objects.create(
            tenant=tenant,
            branch=branch,
            client_type='INDIVIDUAL',
            client_number='CLT-TEST-001',
            full_legal_name='Test Data Client',
            kyc_status='INCOMPLETE',
            risk_rating='LOW',
            assigned_officer=loan_officer_user,
            is_test_data=True,
        )
        assert c.is_test_data is True

    def test_monthly_income_nullable(self, tenant, branch, loan_officer_user, db):
        c = Client.objects.create(
            tenant=tenant,
            branch=branch,
            client_type='INDIVIDUAL',
            client_number='CLT-NOINCOME-01',
            full_legal_name='No Income Declared',
            kyc_status='INCOMPLETE',
            risk_rating='LOW',
            assigned_officer=loan_officer_user,
            monthly_income=None,
        )
        assert c.monthly_income is None

    def test_country_code_2_chars(self, individual_client):
        assert len(individual_client.country) == 2
        assert individual_client.country == 'GH'

    def test_str_representation(self, individual_client):
        result = str(individual_client)
        assert 'Kofi Boateng' in result
        assert 'CLT-2024-00001' in result

    def test_sync_fields(self, individual_client):
        """Clients are offline-capable — must have sync fields."""
        assert individual_client.sync_id is not None
        assert individual_client.sync_status in ['SYNCED', 'PENDING_UPLOAD', 'CONFLICT', 'REJECTED']

    def test_sync_status_choices(self, tenant, branch, loan_officer_user, db):
        for status in ['SYNCED', 'PENDING_UPLOAD', 'CONFLICT', 'REJECTED']:
            c = Client.objects.create(
                tenant=tenant,
                branch=branch,
                client_type='INDIVIDUAL',
                client_number=f'CLT-SYNC-{status[:4]}',
                full_legal_name=f'Sync {status} Client',
                kyc_status='INCOMPLETE',
                risk_rating='LOW',
                assigned_officer=loan_officer_user,
                sync_status=status,
            )
            assert c.sync_status == status


class TestGroup:
    """Group — solidarity/group lending entity."""

    def test_all_fields(self, group_entity, tenant, branch, individual_client):
        g = group_entity
        assert g.tenant == tenant
        assert g.branch == branch
        assert g.group_name == 'Accra Women Traders Group'
        assert g.group_number == 'GRP-2024-00001'
        assert g.leader == individual_client
        assert g.meeting_frequency == 'WEEKLY'
        assert g.meeting_day == 'Monday'
        assert g.is_active is True

    def test_meeting_frequency_choices(self, tenant, branch, db):
        for freq in ['WEEKLY', 'BIWEEKLY', 'MONTHLY']:
            g = Group.objects.create(
                tenant=tenant,
                branch=branch,
                group_name=f'{freq} Traders',
                group_number=f'GRP-FREQ-{freq}',
                meeting_frequency=freq,
            )
            assert g.meeting_frequency == freq

    def test_unique_group_number_per_tenant(self, group_entity, tenant, branch, db):
        with pytest.raises(IntegrityError):
            Group.objects.create(
                tenant=tenant,
                branch=branch,
                group_name='Duplicate Group',
                group_number='GRP-2024-00001',
            )

    def test_leader_nullable(self, tenant, branch, db):
        g = Group.objects.create(
            tenant=tenant,
            branch=branch,
            group_name='No Leader Group',
            group_number='GRP-NOLEAD-01',
            leader=None,
        )
        assert g.leader is None

    def test_sync_fields(self, group_entity):
        assert group_entity.sync_id is not None


class TestGroupMember:
    """GroupMember — client membership in solidarity groups."""

    def test_member_added(self, group_entity, individual_client):
        member = group_entity.members.first()
        assert member is not None
        assert member.client == individual_client
        assert member.joined_at == date(2024, 1, 10)
        assert member.is_active is True
        assert member.left_at is None

    def test_member_exit(self, group_entity, individual_client, db):
        member = group_entity.members.first()
        exit_date = date(2024, 6, 30)
        member.left_at = exit_date
        member.is_active = False
        member.save()
        member.refresh_from_db()
        assert member.left_at == exit_date
        assert member.is_active is False

    def test_unique_group_client(self, group_entity, individual_client, db):
        with pytest.raises(IntegrityError):
            GroupMember.objects.create(
                group=group_entity,
                client=individual_client,
                joined_at=date(2024, 3, 1),
            )

    def test_active_member_count(self, group_entity):
        active = group_entity.members.filter(is_active=True).count()
        assert active == 1


class TestKycDocument:
    """KycDocument — uploaded KYC documents with verification tracking."""

    def test_all_fields(self, kyc_document, tenant, individual_client, loan_officer_user):
        d = kyc_document
        assert d.tenant == tenant
        assert d.client == individual_client
        assert d.document_type == 'ID_SCAN'
        assert d.file_path == 'kyc/CLT-2024-00001/ghana_card_scan.pdf'
        assert d.file_name == 'ghana_card_scan.pdf'
        assert d.file_size_bytes == 256000
        assert d.uploaded_by == loan_officer_user
        assert d.verified is False
        assert d.verified_by is None
        assert d.verified_at is None
        assert d.expiry_date == date(2030, 1, 1)

    def test_document_type_choices(self, tenant, individual_client, loan_officer_user, db):
        doc_types = ['ID_SCAN', 'PROOF_OF_ADDRESS', 'PHOTO', 'SOURCE_OF_FUNDS', 'EDD_REPORT']
        for dtype in doc_types:
            doc = KycDocument.objects.create(
                tenant=tenant,
                client=individual_client,
                document_type=dtype,
                file_path=f'kyc/test/{dtype}.pdf',
                uploaded_by=loan_officer_user,
            )
            assert doc.document_type == dtype

    def test_verification_workflow(self, kyc_document, manager_user, db):
        assert kyc_document.verified is False
        kyc_document.verified = True
        kyc_document.verified_by = manager_user
        kyc_document.verified_at = timezone.now()
        kyc_document.save()
        kyc_document.refresh_from_db()
        assert kyc_document.verified is True
        assert kyc_document.verified_by == manager_user
        assert kyc_document.verified_at is not None

    def test_file_size_tracking(self, kyc_document):
        assert kyc_document.file_size_bytes == 256000

    def test_expiry_date_nullable(self, tenant, individual_client, loan_officer_user, db):
        doc = KycDocument.objects.create(
            tenant=tenant,
            client=individual_client,
            document_type='PHOTO',
            file_path='kyc/photo.jpg',
            uploaded_by=loan_officer_user,
            expiry_date=None,
        )
        assert doc.expiry_date is None

    def test_expired_document_detection(self, kyc_document, db):
        kyc_document.expiry_date = date.today() - timedelta(days=1)
        kyc_document.save()
        expired_docs = KycDocument.objects.filter(
            expiry_date__lt=date.today()
        )
        assert expired_docs.count() == 1

    def test_sync_fields_present(self, kyc_document):
        assert kyc_document.sync_id is not None
        assert kyc_document.sync_status is not None

    def test_multiple_docs_per_client(self, tenant, individual_client, loan_officer_user, db):
        KycDocument.objects.create(
            tenant=tenant,
            client=individual_client,
            document_type='ID_SCAN',
            file_path='kyc/id.pdf',
            uploaded_by=loan_officer_user,
        )
        KycDocument.objects.create(
            tenant=tenant,
            client=individual_client,
            document_type='PROOF_OF_ADDRESS',
            file_path='kyc/address.pdf',
            uploaded_by=loan_officer_user,
        )
        assert individual_client.kyc_documents.count() == 2
