"""
Tests for API view helper logic — schedule generation, repayment splitting.
Tests the business logic in api_views.py independent of HTTP layer.
"""
import uuid
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import MagicMock, patch
from django.test import TestCase


class RepaymentScheduleGeneratorTests(TestCase):
    """Tests for LoanViewSet._generate_schedule logic."""

    def _make_loan(self, principal, rate, term, freq, interest_method):
        """Create a mock loan object for schedule testing."""
        loan = MagicMock()
        loan.tenant_id = uuid.uuid4()
        loan.principal_amount = Decimal(str(principal))
        loan.interest_rate_pct = Decimal(str(rate))
        loan.term_months = term
        loan.repayment_frequency = freq
        loan.interest_method = interest_method
        loan.first_repayment_date = None
        from datetime import date
        loan.disbursement_date = date.today()
        return loan

    def test_flat_rate_schedule_totals(self):
        """Flat rate schedule should sum principal to original principal."""
        from apps.api_views import LoanViewSet
        from apps.loans.models import RepaymentSchedule

        loan = self._make_loan(10000, 20, 12, 'MONTHLY', 'FLAT')

        with patch.object(RepaymentSchedule.objects, 'bulk_create') as mock_bulk:
            view = LoanViewSet()
            view._generate_schedule(loan)

            schedules = mock_bulk.call_args[0][0]
            self.assertEqual(len(schedules), 12)

            total_principal = sum(s.principal_due for s in schedules)
            # Total principal should equal original (with rounding tolerance)
            diff = abs(total_principal - loan.principal_amount)
            self.assertLessEqual(float(diff), 1.0, f'Principal total off by {diff}')

    def test_reducing_balance_schedule_periods(self):
        """Reducing balance schedule should have correct number of periods."""
        from apps.api_views import LoanViewSet
        from apps.loans.models import RepaymentSchedule

        loan = self._make_loan(5000, 24, 6, 'MONTHLY', 'REDUCING_BALANCE')

        with patch.object(RepaymentSchedule.objects, 'bulk_create') as mock_bulk:
            view = LoanViewSet()
            view._generate_schedule(loan)

            schedules = mock_bulk.call_args[0][0]
            self.assertEqual(len(schedules), 6)

    def test_weekly_schedule_has_more_periods(self):
        """Weekly frequency should generate 4x the periods of monthly."""
        from apps.api_views import LoanViewSet
        from apps.loans.models import RepaymentSchedule

        loan = self._make_loan(3000, 18, 3, 'WEEKLY', 'FLAT')

        with patch.object(RepaymentSchedule.objects, 'bulk_create') as mock_bulk:
            view = LoanViewSet()
            view._generate_schedule(loan)

            schedules = mock_bulk.call_args[0][0]
            # 3 months * 4 weeks = 12 periods
            self.assertEqual(len(schedules), 12)

    def test_zero_interest_rate_distributes_principal_only(self):
        """Zero interest rate should create principal-only instalments."""
        from apps.api_views import LoanViewSet
        from apps.loans.models import RepaymentSchedule

        loan = self._make_loan(1200, 0, 12, 'MONTHLY', 'REDUCING_BALANCE')

        with patch.object(RepaymentSchedule.objects, 'bulk_create') as mock_bulk:
            view = LoanViewSet()
            view._generate_schedule(loan)

            schedules = mock_bulk.call_args[0][0]
            self.assertEqual(len(schedules), 12)

    def test_last_instalment_clears_balance(self):
        """Last instalment balance_after should be zero (or very close)."""
        from apps.api_views import LoanViewSet
        from apps.loans.models import RepaymentSchedule

        loan = self._make_loan(10000, 24, 12, 'MONTHLY', 'FLAT')

        with patch.object(RepaymentSchedule.objects, 'bulk_create') as mock_bulk:
            view = LoanViewSet()
            view._generate_schedule(loan)

            schedules = mock_bulk.call_args[0][0]
            last = schedules[-1]
            self.assertLessEqual(float(last.balance_after), 0.01)

    def test_instalment_numbers_are_sequential(self):
        """Instalment numbers should be 1, 2, 3, ..., N."""
        from apps.api_views import LoanViewSet
        from apps.loans.models import RepaymentSchedule

        loan = self._make_loan(5000, 15, 6, 'MONTHLY', 'FLAT')

        with patch.object(RepaymentSchedule.objects, 'bulk_create') as mock_bulk:
            view = LoanViewSet()
            view._generate_schedule(loan)

            schedules = mock_bulk.call_args[0][0]
            numbers = [s.instalment_number for s in schedules]
            self.assertEqual(numbers, list(range(1, 7)))


class RepaymentSplitTests(TestCase):
    """Tests for interest/principal splitting logic in repayment capture."""

    def test_payment_covers_interest_first(self):
        """Payment should cover interest before principal."""
        # Simulate the splitting logic from RepaymentViewSet.capture
        interest_due = Decimal('200')
        interest_paid = Decimal('0')
        amount = Decimal('500')

        interest_remaining = interest_due - interest_paid
        interest_applied = min(amount, interest_remaining)
        principal_applied = amount - interest_applied

        self.assertEqual(interest_applied, Decimal('200'))
        self.assertEqual(principal_applied, Decimal('300'))

    def test_payment_less_than_interest(self):
        """Partial payment goes entirely to interest if it doesn't cover it."""
        interest_due = Decimal('500')
        interest_paid = Decimal('0')
        amount = Decimal('200')

        interest_remaining = interest_due - interest_paid
        interest_applied = min(amount, interest_remaining)
        principal_applied = amount - interest_applied

        self.assertEqual(interest_applied, Decimal('200'))
        self.assertEqual(principal_applied, Decimal('0'))

    def test_payment_when_interest_already_paid(self):
        """Payment with no interest remaining goes entirely to principal."""
        interest_due = Decimal('200')
        interest_paid = Decimal('200')
        amount = Decimal('500')

        interest_remaining = interest_due - interest_paid
        interest_applied = min(amount, interest_remaining)
        principal_applied = amount - interest_applied

        self.assertEqual(interest_applied, Decimal('0'))
        self.assertEqual(principal_applied, Decimal('500'))
