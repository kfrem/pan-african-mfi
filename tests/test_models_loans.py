"""
Tests for LoanProduct, Loan, RepaymentSchedule, and Repayment models.
Validates every field, lifecycle state transition, and financial field precision.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.loans.models import LoanProduct, Loan, RepaymentSchedule, Repayment


pytestmark = pytest.mark.models


class TestLoanProduct:
    """LoanProduct — configurable loan product definitions per tenant."""

    def test_flat_product_all_fields(self, flat_loan_product, tenant):
        p = flat_loan_product
        assert p.tenant == tenant
        assert p.product_code == 'IND-FLAT-01'
        assert p.product_name == 'Individual Flat Loan'
        assert p.product_type == 'INDIVIDUAL'
        assert p.min_amount == Decimal('500.00')
        assert p.max_amount == Decimal('50000.00')
        assert p.min_term_months == 1
        assert p.max_term_months == 24
        assert p.interest_method == 'FLAT'
        assert p.default_interest_rate_pct == Decimal('3.0000')
        assert p.origination_fee_pct == Decimal('2.00')
        assert p.insurance_fee_pct == Decimal('0.50')
        assert p.requires_collateral is False
        assert p.requires_guarantor is False
        assert p.is_active is True
        assert isinstance(p.allowed_frequencies, list)
        assert 'MONTHLY' in p.allowed_frequencies

    def test_reducing_balance_product(self, reducing_loan_product):
        assert reducing_loan_product.interest_method == 'REDUCING_BALANCE'
        assert reducing_loan_product.requires_collateral is True
        assert reducing_loan_product.requires_guarantor is True

    def test_group_product_joint_liability(self, group_loan_product):
        assert group_loan_product.product_type == 'GROUP'
        assert group_loan_product.group_liability_type == 'JOINT'

    def test_product_type_choices(self, tenant, db):
        for ptype in ['INDIVIDUAL', 'GROUP', 'SME', 'EMERGENCY', 'AGRICULTURAL']:
            p = LoanProduct.objects.create(
                tenant=tenant,
                product_code=f'TEST-{ptype}',
                product_name=f'{ptype} Product',
                product_type=ptype,
                min_amount=Decimal('100.00'),
                max_amount=Decimal('10000.00'),
                min_term_months=1,
                max_term_months=12,
                interest_method='FLAT',
                default_interest_rate_pct=Decimal('3.00'),
            )
            assert p.product_type == ptype

    def test_interest_method_choices(self, tenant, db):
        for method in ['FLAT', 'REDUCING_BALANCE']:
            p = LoanProduct.objects.create(
                tenant=tenant,
                product_code=f'TEST-{method}',
                product_name=f'{method} Loan',
                product_type='INDIVIDUAL',
                min_amount=Decimal('100.00'),
                max_amount=Decimal('10000.00'),
                min_term_months=1,
                max_term_months=12,
                interest_method=method,
                default_interest_rate_pct=Decimal('3.00'),
            )
            assert p.interest_method == method

    def test_unique_product_code_per_tenant(self, flat_loan_product, tenant, db):
        with pytest.raises(IntegrityError):
            LoanProduct.objects.create(
                tenant=tenant,
                product_code='IND-FLAT-01',
                product_name='Duplicate Product',
                product_type='INDIVIDUAL',
                min_amount=Decimal('100.00'),
                max_amount=Decimal('5000.00'),
                min_term_months=1,
                max_term_months=12,
                interest_method='FLAT',
                default_interest_rate_pct=Decimal('3.00'),
            )

    def test_fee_pct_decimal_precision(self, flat_loan_product):
        """Fees must carry 2 decimal places for accuracy."""
        assert flat_loan_product.origination_fee_pct == Decimal('2.00')
        assert flat_loan_product.insurance_fee_pct == Decimal('0.50')

    def test_str_representation(self, flat_loan_product):
        result = str(flat_loan_product)
        assert 'Individual Flat Loan' in result

    def test_allowed_frequencies_json_field(self, flat_loan_product):
        assert isinstance(flat_loan_product.allowed_frequencies, list)
        assert len(flat_loan_product.allowed_frequencies) > 0

    def test_amount_range_integrity(self, flat_loan_product):
        """min_amount must be less than max_amount."""
        assert flat_loan_product.min_amount < flat_loan_product.max_amount

    def test_term_range_integrity(self, flat_loan_product):
        """min_term must be less than max_term."""
        assert flat_loan_product.min_term_months < flat_loan_product.max_term_months


class TestLoan:
    """Loan — core loan record tracking full lifecycle."""

    def test_pending_loan_all_fields(self, pending_loan, tenant, branch, verified_client,
                                      flat_loan_product, loan_officer_user):
        l = pending_loan
        assert l.tenant == tenant
        assert l.loan_number == 'LN-202401-00001'
        assert l.client == verified_client
        assert l.product == flat_loan_product
        assert l.branch == branch
        assert l.loan_officer == loan_officer_user
        assert l.principal_amount == Decimal('5000.00')
        assert l.currency == 'GHS'
        assert l.interest_rate_pct == Decimal('3.0000')
        assert l.interest_method == 'FLAT'
        assert l.term_months == 12
        assert l.repayment_frequency == 'MONTHLY'
        assert l.origination_fee > Decimal('0')
        assert l.total_repayable > l.principal_amount
        assert l.outstanding_principal == Decimal('5000.00')
        assert l.days_past_due == 0
        assert l.status == 'PENDING_APPROVAL'
        assert l.classification == 'CURRENT'
        assert l.provision_rate_pct == Decimal('1.00')
        assert l.application_date == date.today()
        assert l.is_insider_loan is False
        assert l.override_flag is False
        assert l.created_at is not None

    def test_pending_loan_status(self, pending_loan):
        assert pending_loan.status == 'PENDING_APPROVAL'

    def test_approved_loan_status(self, approved_loan):
        assert approved_loan.status == 'APPROVED'

    def test_disbursed_loan_status(self, disbursed_loan):
        assert disbursed_loan.status == 'DISBURSED'

    def test_approval_sets_approved_by(self, approved_loan, manager_user):
        assert approved_loan.approved_by == manager_user
        assert approved_loan.approval_date == date.today()

    def test_disbursement_sets_disbursed_by(self, disbursed_loan, manager_user):
        assert disbursed_loan.disbursed_by == manager_user
        assert disbursed_loan.disbursement_date == date.today()
        assert disbursed_loan.maturity_date is not None

    def test_status_choices(self, tenant, branch, verified_client, flat_loan_product, loan_officer_user, db):
        statuses = ['APPLICATION', 'PENDING_APPROVAL', 'APPROVED', 'DISBURSED',
                    'ACTIVE', 'CLOSED', 'WRITTEN_OFF', 'RESTRUCTURED']
        for i, status in enumerate(statuses):
            l = Loan.objects.create(
                tenant=tenant,
                loan_number=f'LN-STAT-{i:05d}',
                client=verified_client,
                product=flat_loan_product,
                branch=branch,
                loan_officer=loan_officer_user,
                principal_amount=Decimal('1000.00'),
                currency='GHS',
                interest_rate_pct=Decimal('3.00'),
                interest_method='FLAT',
                term_months=6,
                repayment_frequency='MONTHLY',
                total_repayable=Decimal('1090.00'),
                outstanding_principal=Decimal('1000.00'),
                application_date=date.today(),
                status=status,
            )
            assert l.status == status

    def test_classification_choices(self, tenant, branch, verified_client, flat_loan_product, loan_officer_user, db):
        for i, cls in enumerate(['CURRENT', 'WATCH', 'SUBSTANDARD', 'DOUBTFUL', 'LOSS']):
            l = Loan.objects.create(
                tenant=tenant,
                loan_number=f'LN-CLS-{i:05d}',
                client=verified_client,
                product=flat_loan_product,
                branch=branch,
                loan_officer=loan_officer_user,
                principal_amount=Decimal('1000.00'),
                currency='GHS',
                interest_rate_pct=Decimal('3.00'),
                interest_method='FLAT',
                term_months=6,
                repayment_frequency='MONTHLY',
                total_repayable=Decimal('1090.00'),
                outstanding_principal=Decimal('1000.00'),
                application_date=date.today(),
                classification=cls,
            )
            assert l.classification == cls

    def test_overdue_loan_fields(self, overdue_loan):
        assert overdue_loan.days_past_due == 45
        assert overdue_loan.classification == 'WATCH'
        assert overdue_loan.provision_rate_pct == Decimal('5.00')
        assert overdue_loan.arrears_amount > Decimal('0')

    def test_loss_classification_100_percent_provision(self, loss_loan):
        assert loss_loan.classification == 'LOSS'
        assert loss_loan.provision_rate_pct == Decimal('100.00')
        assert loss_loan.provision_amount == loss_loan.outstanding_principal

    def test_insider_loan_flagged(self, insider_loan):
        assert insider_loan.is_insider_loan is True
        assert insider_loan.client.is_insider is True

    def test_repayment_frequency_choices(self, tenant, branch, verified_client, flat_loan_product, loan_officer_user, db):
        for i, freq in enumerate(['DAILY', 'WEEKLY', 'FORTNIGHTLY', 'MONTHLY']):
            l = Loan.objects.create(
                tenant=tenant,
                loan_number=f'LN-FREQ-{i:05d}',
                client=verified_client,
                product=flat_loan_product,
                branch=branch,
                loan_officer=loan_officer_user,
                principal_amount=Decimal('1000.00'),
                currency='GHS',
                interest_rate_pct=Decimal('3.00'),
                interest_method='FLAT',
                term_months=6,
                repayment_frequency=freq,
                total_repayable=Decimal('1090.00'),
                outstanding_principal=Decimal('1000.00'),
                application_date=date.today(),
            )
            assert l.repayment_frequency == freq

    def test_unique_loan_number_per_tenant(self, pending_loan, tenant, branch, verified_client,
                                            flat_loan_product, loan_officer_user, db):
        with pytest.raises(IntegrityError):
            Loan.objects.create(
                tenant=tenant,
                loan_number='LN-202401-00001',
                client=verified_client,
                product=flat_loan_product,
                branch=branch,
                loan_officer=loan_officer_user,
                principal_amount=Decimal('2000.00'),
                currency='GHS',
                interest_rate_pct=Decimal('3.00'),
                interest_method='FLAT',
                term_months=6,
                repayment_frequency='MONTHLY',
                total_repayable=Decimal('2060.00'),
                outstanding_principal=Decimal('2000.00'),
                application_date=date.today(),
            )

    def test_sync_fields_present(self, pending_loan):
        assert pending_loan.sync_id is not None
        assert pending_loan.sync_status is not None

    def test_outstanding_principal_starts_at_principal(self, pending_loan):
        assert pending_loan.outstanding_principal == pending_loan.principal_amount

    def test_total_repayable_greater_than_principal(self, pending_loan):
        assert pending_loan.total_repayable > pending_loan.principal_amount

    def test_origination_fee_calculated_correctly(self, pending_loan, flat_loan_product):
        expected_fee = pending_loan.principal_amount * (flat_loan_product.origination_fee_pct / 100)
        assert pending_loan.origination_fee == expected_fee

    def test_affordability_dti_nullable(self, pending_loan):
        assert pending_loan.affordability_dti_pct is None

    def test_collateral_fields(self, tenant, branch, verified_client, flat_loan_product, loan_officer_user, db):
        l = Loan.objects.create(
            tenant=tenant,
            loan_number='LN-COLL-00001',
            client=verified_client,
            product=flat_loan_product,
            branch=branch,
            loan_officer=loan_officer_user,
            principal_amount=Decimal('10000.00'),
            currency='GHS',
            interest_rate_pct=Decimal('3.00'),
            interest_method='FLAT',
            term_months=12,
            repayment_frequency='MONTHLY',
            total_repayable=Decimal('10900.00'),
            outstanding_principal=Decimal('10000.00'),
            application_date=date.today(),
            collateral_description='2019 Toyota Hilux, Reg: GR 1234-20',
            collateral_value=Decimal('45000.00'),
        )
        assert l.collateral_description != ''
        assert l.collateral_value == Decimal('45000.00')

    def test_closed_loan_fields(self, disbursed_loan, db):
        disbursed_loan.status = 'CLOSED'
        disbursed_loan.closed_date = date.today()
        disbursed_loan.outstanding_principal = Decimal('0.00')
        disbursed_loan.save()
        assert disbursed_loan.status == 'CLOSED'
        assert disbursed_loan.closed_date == date.today()

    def test_str_representation(self, pending_loan):
        result = str(pending_loan)
        assert 'LN-202401-00001' in result


class TestRepaymentSchedule:
    """RepaymentSchedule — expected instalments generated at disbursement."""

    def test_all_fields(self, repayment_schedule, disbursed_loan, tenant):
        s = repayment_schedule
        assert s.tenant == tenant
        assert s.loan == disbursed_loan
        assert s.instalment_number == 1
        assert s.due_date == date.today() + timedelta(days=30)
        assert s.principal_due == Decimal('416.67')
        assert s.interest_due == Decimal('150.00')
        assert s.fees_due == Decimal('0.00')
        assert s.total_due == Decimal('566.67')
        assert s.principal_paid == Decimal('0.00')
        assert s.interest_paid == Decimal('0.00')
        assert s.total_paid == Decimal('0.00')
        assert s.balance_after == Decimal('4583.33')
        assert s.status == 'PENDING'
        assert s.days_late == 0

    def test_status_choices(self, disbursed_loan, tenant, db):
        for i, status in enumerate(['PENDING', 'PAID', 'PARTIAL', 'OVERDUE']):
            RepaymentSchedule.objects.create(
                tenant=tenant,
                loan=disbursed_loan,
                instalment_number=i + 10,
                due_date=date.today() + timedelta(days=30 * (i + 2)),
                principal_due=Decimal('416.67'),
                interest_due=Decimal('150.00'),
                total_due=Decimal('566.67'),
                status=status,
            )

    def test_unique_instalment_per_loan(self, repayment_schedule, disbursed_loan, tenant, db):
        with pytest.raises(IntegrityError):
            RepaymentSchedule.objects.create(
                tenant=tenant,
                loan=disbursed_loan,
                instalment_number=1,  # duplicate
                due_date=date.today() + timedelta(days=60),
                principal_due=Decimal('416.67'),
                interest_due=Decimal('150.00'),
                total_due=Decimal('566.67'),
            )

    def test_partial_payment_tracking(self, repayment_schedule, db):
        repayment_schedule.principal_paid = Decimal('200.00')
        repayment_schedule.interest_paid = Decimal('75.00')
        repayment_schedule.total_paid = Decimal('275.00')
        repayment_schedule.status = 'PARTIAL'
        repayment_schedule.save()
        repayment_schedule.refresh_from_db()
        assert repayment_schedule.status == 'PARTIAL'
        assert repayment_schedule.total_paid == Decimal('275.00')

    def test_paid_date_set_on_full_payment(self, repayment_schedule, db):
        repayment_schedule.principal_paid = Decimal('416.67')
        repayment_schedule.interest_paid = Decimal('150.00')
        repayment_schedule.total_paid = Decimal('566.67')
        repayment_schedule.status = 'PAID'
        repayment_schedule.paid_date = date.today()
        repayment_schedule.save()
        assert repayment_schedule.paid_date == date.today()

    def test_days_late_tracking(self, repayment_schedule, db):
        repayment_schedule.due_date = date.today() - timedelta(days=15)
        repayment_schedule.status = 'OVERDUE'
        repayment_schedule.days_late = 15
        repayment_schedule.save()
        assert repayment_schedule.days_late == 15

    def test_total_due_equals_principal_plus_interest(self, repayment_schedule):
        expected = repayment_schedule.principal_due + repayment_schedule.interest_due + repayment_schedule.fees_due
        assert repayment_schedule.total_due == expected


class TestRepayment:
    """Repayment — actual payments received, with allocation and reversal support."""

    def test_creation(self, tenant, disbursed_loan, repayment_schedule, loan_officer_user, db):
        r = Repayment.objects.create(
            tenant=tenant,
            loan=disbursed_loan,
            schedule=repayment_schedule,
            amount=Decimal('566.67'),
            currency='GHS',
            payment_method='CASH',
            payment_reference='',
            received_by=loan_officer_user,
            received_at=timezone.now(),
            principal_applied=Decimal('416.67'),
            interest_applied=Decimal('150.00'),
            fees_applied=Decimal('0.00'),
            penalty_applied=Decimal('0.00'),
            receipt_number='RCP-20240101-000001',
            reversed=False,
        )
        assert r.amount == Decimal('566.67')
        assert r.payment_method == 'CASH'
        assert r.reversed is False
        assert r.receipt_number == 'RCP-20240101-000001'

    def test_payment_method_choices(self, tenant, disbursed_loan, loan_officer_user, db):
        for i, method in enumerate(['CASH', 'MOBILE_MONEY', 'BANK_TRANSFER', 'CHEQUE']):
            r = Repayment.objects.create(
                tenant=tenant,
                loan=disbursed_loan,
                amount=Decimal('100.00'),
                currency='GHS',
                payment_method=method,
                received_by=loan_officer_user,
                received_at=timezone.now(),
                principal_applied=Decimal('80.00'),
                interest_applied=Decimal('20.00'),
                receipt_number=f'RCP-TEST-{i:06d}',
            )
            assert r.payment_method == method

    def test_reversal_fields(self, tenant, disbursed_loan, repayment_schedule, loan_officer_user, manager_user, db):
        r = Repayment.objects.create(
            tenant=tenant,
            loan=disbursed_loan,
            schedule=repayment_schedule,
            amount=Decimal('566.67'),
            currency='GHS',
            payment_method='CASH',
            received_by=loan_officer_user,
            received_at=timezone.now(),
            principal_applied=Decimal('416.67'),
            interest_applied=Decimal('150.00'),
            receipt_number='RCP-REV-000001',
        )
        # Reverse the payment
        r.reversed = True
        r.reversed_by = manager_user
        r.reversed_at = timezone.now()
        r.reversal_reason = 'Duplicate payment captured'
        r.save()
        r.refresh_from_db()
        assert r.reversed is True
        assert r.reversed_by == manager_user
        assert 'Duplicate' in r.reversal_reason

    def test_amount_allocation(self, tenant, disbursed_loan, loan_officer_user, db):
        """Principal + interest + fees must equal total amount."""
        principal = Decimal('416.67')
        interest = Decimal('150.00')
        fees = Decimal('0.00')
        total = principal + interest + fees
        r = Repayment.objects.create(
            tenant=tenant,
            loan=disbursed_loan,
            amount=total,
            currency='GHS',
            payment_method='MOBILE_MONEY',
            received_by=loan_officer_user,
            received_at=timezone.now(),
            principal_applied=principal,
            interest_applied=interest,
            fees_applied=fees,
            receipt_number='RCP-ALLOC-000001',
        )
        assert r.principal_applied + r.interest_applied + r.fees_applied == total

    def test_sync_fields(self, tenant, disbursed_loan, loan_officer_user, db):
        r = Repayment.objects.create(
            tenant=tenant,
            loan=disbursed_loan,
            amount=Decimal('100.00'),
            currency='GHS',
            payment_method='CASH',
            received_by=loan_officer_user,
            received_at=timezone.now(),
            principal_applied=Decimal('80.00'),
            interest_applied=Decimal('20.00'),
            receipt_number='RCP-SYNC-000001',
            device_id='device-uuid-abc123',
            sync_status='SYNCED',
        )
        assert r.device_id == 'device-uuid-abc123'
        assert r.sync_id is not None

    def test_penalty_applied_field(self, tenant, disbursed_loan, loan_officer_user, db):
        r = Repayment.objects.create(
            tenant=tenant,
            loan=disbursed_loan,
            amount=Decimal('600.00'),
            currency='GHS',
            payment_method='CASH',
            received_by=loan_officer_user,
            received_at=timezone.now(),
            principal_applied=Decimal('416.67'),
            interest_applied=Decimal('150.00'),
            penalty_applied=Decimal('33.33'),
            receipt_number='RCP-PEN-000001',
        )
        assert r.penalty_applied == Decimal('33.33')
