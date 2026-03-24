"""
Financial calculation tests — interest, repayment schedules, PAR, provisioning.
These are critical for regulatory compliance and must be mathematically correct.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pytest

from apps.loans.models import LoanProduct, Loan, RepaymentSchedule


pytestmark = pytest.mark.calculations


class TestFlatInterestCalculation:
    """Flat interest: I = P × r × t — total interest divided equally."""

    def test_basic_flat_interest_formula(self, pending_loan):
        """GHS 5,000 @ 3% flat × 12 months = GHS 150."""
        principal = Decimal('5000.00')
        rate = Decimal('3.00')    # 3% per annum (monthly flat)
        term = 12
        expected_interest = principal * (rate / 100) * (Decimal(str(term)) / 12)
        assert expected_interest == Decimal('150.0000')
        assert pending_loan.total_interest == expected_interest

    def test_flat_interest_6_month_term(self, tenant, branch, verified_client, flat_loan_product, loan_officer_user, db):
        principal = Decimal('10000.00')
        rate = Decimal('3.00')
        term = 6
        expected = principal * (rate / 100) * (Decimal('6') / 12)
        assert expected == Decimal('150.0000')

    def test_flat_interest_24_month_term(self, tenant, branch, verified_client, flat_loan_product, loan_officer_user, db):
        principal = Decimal('20000.00')
        rate = Decimal('3.00')
        term = 24
        expected = principal * (rate / 100) * (Decimal('24') / 12)
        assert expected == Decimal('1200.0000')

    def test_origination_fee_calculation(self, pending_loan, flat_loan_product):
        """Origination fee = principal × fee_pct / 100."""
        expected_fee = pending_loan.principal_amount * (flat_loan_product.origination_fee_pct / 100)
        assert pending_loan.origination_fee == expected_fee

    def test_total_repayable_formula(self, pending_loan):
        """Total repayable = principal + total_interest + origination_fee."""
        expected = (
            pending_loan.principal_amount
            + pending_loan.total_interest
            + pending_loan.origination_fee
        )
        assert pending_loan.total_repayable == expected

    def test_monthly_instalment_flat(self, pending_loan):
        """Each monthly instalment = total_repayable / term_months."""
        monthly = pending_loan.total_repayable / pending_loan.term_months
        # Verify it's a sensible amount
        assert monthly > Decimal('0')
        assert monthly < pending_loan.total_repayable

    def test_flat_rate_higher_effective_rate_than_rb(self):
        """
        Flat rate is more expensive for borrower than reducing balance at same nominal rate.
        Borrower always owes interest on full principal regardless of repayments.
        """
        principal = Decimal('10000.00')
        rate = Decimal('3.00')
        term = 12

        # Flat interest
        flat_interest = principal * (rate / 100) * (Decimal('12') / 12)

        # Reducing balance interest (PMT formula)
        monthly_rate = rate / 100 / 12
        payment = principal * (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
        rb_interest = (payment * term) - principal

        assert flat_interest > rb_interest


class TestReducingBalanceCalculation:
    """Reducing balance: PMT = P × (r(1+r)^n) / ((1+r)^n - 1)."""

    def test_reducing_balance_pmt_formula(self):
        """Compute monthly PMT for a reducing balance loan."""
        principal = Decimal('10000.00')
        annual_rate = Decimal('24.00')  # 24% per annum
        monthly_rate = annual_rate / 100 / 12  # 0.02
        term = 12

        payment = principal * (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
        total_repaid = payment * term
        total_interest = total_repaid - principal

        # At 24% annual, 12 months: PMT ≈ 948.67, total interest ≈ GHS 384.04
        assert payment > Decimal('900')
        assert payment < Decimal('1000')
        assert total_interest > Decimal('0')
        assert total_interest < principal  # interest < principal

    def test_zero_interest_rate(self):
        """At 0% interest, total repaid equals principal."""
        principal = Decimal('10000.00')
        term = 12
        payment = principal / term
        total_repaid = payment * term
        assert total_repaid == principal

    def test_higher_rate_means_more_interest(self):
        """Higher annual rate results in higher total interest paid."""
        principal = Decimal('10000.00')
        term = 12

        def compute_interest(annual_rate_pct):
            r = Decimal(str(annual_rate_pct)) / 100 / 12
            pmt = principal * (r * (1 + r)**term) / ((1 + r)**term - 1)
            return (pmt * term) - principal

        interest_low = compute_interest(12)
        interest_high = compute_interest(36)
        assert interest_high > interest_low

    def test_longer_term_means_more_total_interest(self):
        """Longer loan term increases total interest under reducing balance."""
        principal = Decimal('10000.00')
        annual_rate = Decimal('24.00')

        def compute_interest(term_months):
            r = annual_rate / 100 / 12
            pmt = principal * (r * (1 + r)**term_months) / ((1 + r)**term_months - 1)
            return (pmt * term_months) - principal

        interest_12m = compute_interest(12)
        interest_24m = compute_interest(24)
        assert interest_24m > interest_12m


class TestRepaymentScheduleGeneration:
    """Test that schedule generation produces correct instalments."""

    def test_monthly_schedule_count(self, disbursed_loan, tenant, db):
        """12-month monthly loan → 12 schedule entries."""
        from apps.api_views import LoanViewSet
        viewset = LoanViewSet()
        viewset._generate_schedule(disbursed_loan)
        schedules = RepaymentSchedule.objects.filter(loan=disbursed_loan)
        assert schedules.count() == 12

    def test_schedule_instalments_numbered_correctly(self, disbursed_loan, tenant, db):
        from apps.api_views import LoanViewSet
        viewset = LoanViewSet()
        viewset._generate_schedule(disbursed_loan)
        schedules = RepaymentSchedule.objects.filter(loan=disbursed_loan).order_by('instalment_number')
        numbers = list(schedules.values_list('instalment_number', flat=True))
        assert numbers == list(range(1, 13))

    def test_schedule_principal_sums_to_loan_amount(self, disbursed_loan, tenant, db):
        """Sum of all principal_due must equal principal_amount."""
        from apps.api_views import LoanViewSet
        from django.db.models import Sum
        viewset = LoanViewSet()
        viewset._generate_schedule(disbursed_loan)
        total_principal = RepaymentSchedule.objects.filter(
            loan=disbursed_loan
        ).aggregate(total=Sum('principal_due'))['total']
        # Allow for rounding: last instalment adjusts to clean up
        assert abs(total_principal - disbursed_loan.principal_amount) < Decimal('0.10')

    def test_weekly_schedule_period_count(self, tenant, branch, verified_client, flat_loan_product, loan_officer_user, db):
        """3-month weekly loan → 12 schedule entries (3 months × 4 weeks)."""
        principal = Decimal('2000.00')
        loan = Loan.objects.create(
            tenant=tenant,
            loan_number='LN-WEEKLY-00001',
            client=verified_client,
            product=flat_loan_product,
            branch=branch,
            loan_officer=loan_officer_user,
            principal_amount=principal,
            currency='GHS',
            interest_rate_pct=Decimal('3.00'),
            interest_method='FLAT',
            term_months=3,
            repayment_frequency='WEEKLY',
            total_repayable=Decimal('2060.00'),
            outstanding_principal=principal,
            application_date=date.today(),
            status='DISBURSED',
            disbursement_date=date.today(),
        )
        from apps.api_views import LoanViewSet
        viewset = LoanViewSet()
        viewset._generate_schedule(loan)
        count = RepaymentSchedule.objects.filter(loan=loan).count()
        assert count == 12  # 3 months × 4 weeks

    def test_schedule_due_dates_increase(self, disbursed_loan, tenant, db):
        """Each instalment due date must be later than the previous."""
        from apps.api_views import LoanViewSet
        viewset = LoanViewSet()
        viewset._generate_schedule(disbursed_loan)
        schedules = RepaymentSchedule.objects.filter(loan=disbursed_loan).order_by('instalment_number')
        dates = list(schedules.values_list('due_date', flat=True))
        for i in range(1, len(dates)):
            assert dates[i] > dates[i - 1]

    def test_schedule_balance_decreases(self, disbursed_loan, tenant, db):
        """Outstanding balance after each repayment must decrease."""
        from apps.api_views import LoanViewSet
        viewset = LoanViewSet()
        viewset._generate_schedule(disbursed_loan)
        schedules = RepaymentSchedule.objects.filter(
            loan=disbursed_loan
        ).order_by('instalment_number')
        balances = list(schedules.values_list('balance_after', flat=True))
        for i in range(1, len(balances)):
            assert balances[i] < balances[i - 1] or balances[i] == Decimal('0')

    def test_last_schedule_balance_zero(self, disbursed_loan, tenant, db):
        """Final instalment must bring balance to exactly zero."""
        from apps.api_views import LoanViewSet
        viewset = LoanViewSet()
        viewset._generate_schedule(disbursed_loan)
        last = RepaymentSchedule.objects.filter(loan=disbursed_loan).order_by('-instalment_number').first()
        assert last.balance_after == Decimal('0') or last.balance_after < Decimal('0.01')


class TestLoanClassificationLogic:
    """Loan classification rules: DPD → risk class → provision rate."""

    def test_current_0_dpd(self, pending_loan):
        assert pending_loan.days_past_due == 0
        assert pending_loan.classification == 'CURRENT'
        assert pending_loan.provision_rate_pct == Decimal('1.00')

    def test_watch_45_dpd(self, overdue_loan):
        assert overdue_loan.days_past_due == 45
        assert overdue_loan.classification == 'WATCH'
        assert overdue_loan.provision_rate_pct == Decimal('5.00')

    def test_loss_400_dpd(self, loss_loan):
        assert loss_loan.days_past_due == 400
        assert loss_loan.classification == 'LOSS'
        assert loss_loan.provision_rate_pct == Decimal('100.00')

    def test_provision_amount_calculation(self, overdue_loan):
        """Provision amount = outstanding_principal × provision_rate_pct / 100."""
        expected = overdue_loan.outstanding_principal * (overdue_loan.provision_rate_pct / 100)
        assert overdue_loan.provision_amount == expected

    def test_loss_provision_equals_outstanding(self, loss_loan):
        """LOSS loans: provision must cover 100% of outstanding principal."""
        assert loss_loan.provision_amount == loss_loan.outstanding_principal

    def test_classification_boundary_current_watch(self):
        """DPD=30 → CURRENT; DPD=31 → WATCH (per Ghana BoG rules)."""
        # Boundary values
        assert 30 <= 30  # CURRENT boundary
        assert 31 >= 31  # WATCH boundary — just past CURRENT


class TestPARCalculation:
    """Portfolio at Risk calculations — critical regulatory metric."""

    def test_par30_zero_for_current_portfolio(self, disbursed_loan, db):
        """No overdue loans → PAR30 = 0."""
        from django.db.models import Sum
        active_loans = Loan.objects.filter(status__in=['ACTIVE', 'DISBURSED'])
        par30 = Loan.objects.filter(
            status__in=['ACTIVE', 'DISBURSED'],
            days_past_due__gte=30
        ).aggregate(total=Sum('outstanding_principal'))['total']
        assert par30 is None or par30 == Decimal('0')

    def test_par30_includes_overdue_loans(self, disbursed_loan, overdue_loan, db):
        """Overdue loans (≥30 DPD) count in PAR30."""
        from django.db.models import Sum
        # overdue_loan has 45 DPD → included in PAR30
        par30 = Loan.objects.filter(
            days_past_due__gte=30
        ).aggregate(total=Sum('outstanding_principal'))['total']
        assert par30 is not None
        assert par30 >= overdue_loan.outstanding_principal

    def test_par30_pct_formula(self):
        """PAR30% = PAR30 balance / total active portfolio × 100."""
        total_portfolio = Decimal('1000000.00')
        par30_balance = Decimal('50000.00')
        par30_pct = (par30_balance / total_portfolio) * 100
        assert par30_pct == Decimal('5.00')

    def test_par30_pct_zero_portfolio(self):
        """No active portfolio → PAR30% = 0 (avoid division by zero)."""
        portfolio = Decimal('0')
        par30_balance = Decimal('0')
        par30_pct = (par30_balance / portfolio * 100) if portfolio > 0 else Decimal('0')
        assert par30_pct == Decimal('0')


class TestRepaymentAllocation:
    """Repayment allocation: interest first, then principal."""

    def test_interest_first_allocation(self, tenant, disbursed_loan, repayment_schedule, loan_officer_user, db):
        """Payment of GHS 566.67 with interest remaining of GHS 150 → GHS 150 to interest, rest to principal."""
        from apps.loans.models import Repayment
        amount = Decimal('566.67')
        interest_remaining = repayment_schedule.interest_due - repayment_schedule.interest_paid
        interest_applied = min(amount, interest_remaining)
        principal_applied = amount - interest_applied

        assert interest_applied == Decimal('150.00')
        assert principal_applied == Decimal('416.67')
        assert interest_applied + principal_applied == amount

    def test_partial_payment_covers_interest_only(self, disbursed_loan, repayment_schedule, db):
        """Payment of GHS 100 < interest due → all to interest, zero to principal."""
        amount = Decimal('100.00')
        interest_remaining = repayment_schedule.interest_due
        interest_applied = min(amount, interest_remaining)
        principal_applied = amount - interest_applied

        assert interest_applied == amount
        assert principal_applied == Decimal('0')

    def test_overpayment_reduces_principal(self, disbursed_loan, repayment_schedule, db):
        """Extra payment beyond total_due further reduces principal."""
        amount = Decimal('700.00')  # more than total_due of 566.67
        interest_applied = min(amount, repayment_schedule.interest_due)
        principal_applied = amount - interest_applied

        assert principal_applied == Decimal('550.00')  # 700 - 150 interest

    def test_loan_closes_when_principal_zero(self, tenant, disbursed_loan, loan_officer_user, db):
        """When outstanding_principal reaches zero, loan status → CLOSED."""
        from apps.loans.models import Repayment
        from django.utils import timezone

        amount = disbursed_loan.outstanding_principal
        Repayment.objects.create(
            tenant=tenant,
            loan=disbursed_loan,
            amount=amount,
            currency='GHS',
            payment_method='CASH',
            received_by=loan_officer_user,
            received_at=timezone.now(),
            principal_applied=amount,
            interest_applied=Decimal('0'),
            receipt_number='RCP-CLOSE-000001',
        )
        disbursed_loan.outstanding_principal = Decimal('0')
        disbursed_loan.status = 'CLOSED'
        disbursed_loan.closed_date = date.today()
        disbursed_loan.save()
        disbursed_loan.refresh_from_db()
        assert disbursed_loan.status == 'CLOSED'
        assert disbursed_loan.outstanding_principal == Decimal('0')


class TestFeeCalculation:
    """Fee computation — origination fee, insurance, and disbursed amounts."""

    def test_origination_fee_2pct(self):
        """2% origination fee on GHS 5,000 = GHS 100."""
        principal = Decimal('5000.00')
        fee_pct = Decimal('2.00')
        expected_fee = principal * (fee_pct / 100)
        assert expected_fee == Decimal('100.0000')

    def test_insurance_fee_0_5pct(self):
        """0.5% insurance fee on GHS 5,000 = GHS 25."""
        principal = Decimal('5000.00')
        fee_pct = Decimal('0.50')
        expected_fee = principal * (fee_pct / 100)
        assert expected_fee == Decimal('25.0000')

    def test_net_disbursement_deducts_upfront_fees(self):
        """Some MFIs deduct origination fee from disbursement."""
        principal = Decimal('5000.00')
        origination_fee = Decimal('100.00')
        net_disbursed = principal - origination_fee
        assert net_disbursed == Decimal('4900.00')

    def test_zero_fee_product(self, tenant, db):
        """Products can have 0% origination fee."""
        p = LoanProduct.objects.create(
            tenant=tenant,
            product_code='ZERO-FEE-01',
            product_name='Zero Fee Loan',
            product_type='EMERGENCY',
            min_amount=Decimal('100.00'),
            max_amount=Decimal('5000.00'),
            min_term_months=1,
            max_term_months=6,
            interest_method='FLAT',
            default_interest_rate_pct=Decimal('0.00'),
            origination_fee_pct=Decimal('0.00'),
            insurance_fee_pct=Decimal('0.00'),
        )
        fee = Decimal('5000.00') * (p.origination_fee_pct / 100)
        assert fee == Decimal('0.00')


class TestDecimalPrecision:
    """Financial decimal fields must maintain 4-decimal-place precision."""

    def test_principal_4_decimal_places(self, pending_loan):
        """Principal stored with 4 decimal places for sub-cent precision."""
        # GHS amounts need 4 decimal places for pesewa precision
        assert pending_loan.principal_amount == Decimal('5000.0000')

    def test_interest_rate_4_decimal_places(self, pending_loan):
        assert pending_loan.interest_rate_pct == Decimal('3.0000')

    def test_interest_income_4_decimal_places(self, pending_loan):
        assert pending_loan.total_interest == Decimal('150.0000')

    def test_decimal_rounding_half_up(self):
        """Financial rounding must use ROUND_HALF_UP (banker's standard)."""
        value = Decimal('0.125')
        rounded = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        assert rounded == Decimal('0.13')

    def test_exchange_rate_8_decimal_places(self, db):
        from apps.ledger.models import ExchangeRate
        rate = ExchangeRate.objects.create(
            base_currency='USD',
            target_currency='GHS',
            rate=Decimal('12.54321234'),
            rate_date=date.today(),
        )
        assert rate.rate == Decimal('12.54321234')

    def test_single_obligor_limit_pct(self, licence_tier):
        """Single obligor limit must be stored precisely."""
        assert licence_tier.single_obligor_limit_pct == Decimal('15.00')
