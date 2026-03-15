"""
Tests for API serializers — validates that serializers correctly
handle model data, read_only fields, and computed properties.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase


class RepaymentCaptureSerializerTests(TestCase):
    """Tests for RepaymentCaptureSerializer."""

    def test_valid_repayment_data(self):
        from apps.api_serializers import RepaymentCaptureSerializer
        from django.utils import timezone

        data = {
            'loan_id': str(uuid.uuid4()),
            'amount': '500.00',
            'payment_method': 'CASH',
            'received_at': timezone.now().isoformat(),
        }
        serializer = RepaymentCaptureSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_payment_method(self):
        from apps.api_serializers import RepaymentCaptureSerializer
        from django.utils import timezone

        data = {
            'loan_id': str(uuid.uuid4()),
            'amount': '500.00',
            'payment_method': 'CRYPTO',  # invalid
            'received_at': timezone.now().isoformat(),
        }
        serializer = RepaymentCaptureSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('payment_method', serializer.errors)

    def test_missing_required_fields(self):
        from apps.api_serializers import RepaymentCaptureSerializer

        serializer = RepaymentCaptureSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('loan_id', serializer.errors)
        self.assertIn('amount', serializer.errors)


class LoanApplicationSerializerTests(TestCase):
    """Tests for LoanApplicationSerializer."""

    def test_valid_loan_application(self):
        from apps.api_serializers import LoanApplicationSerializer

        data = {
            'client_id': str(uuid.uuid4()),
            'product_id': str(uuid.uuid4()),
            'branch_id': str(uuid.uuid4()),
            'principal_amount': '10000.00',
            'term_months': 12,
            'repayment_frequency': 'MONTHLY',
        }
        serializer = LoanApplicationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_repayment_frequency(self):
        from apps.api_serializers import LoanApplicationSerializer

        data = {
            'client_id': str(uuid.uuid4()),
            'product_id': str(uuid.uuid4()),
            'branch_id': str(uuid.uuid4()),
            'principal_amount': '10000.00',
            'term_months': 12,
            'repayment_frequency': 'QUARTERLY',  # not in choices
        }
        serializer = LoanApplicationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('repayment_frequency', serializer.errors)

    def test_term_months_must_be_positive(self):
        from apps.api_serializers import LoanApplicationSerializer

        data = {
            'client_id': str(uuid.uuid4()),
            'product_id': str(uuid.uuid4()),
            'branch_id': str(uuid.uuid4()),
            'principal_amount': '10000.00',
            'term_months': 0,  # must be >= 1
            'repayment_frequency': 'MONTHLY',
        }
        serializer = LoanApplicationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('term_months', serializer.errors)


class CollectRepaymentSerializerTests(TestCase):
    """Tests for CollectRepaymentSerializer (Mobile Money)."""

    def test_valid_collect_request(self):
        from apps.api_serializers import CollectRepaymentSerializer

        data = {
            'loan_id': str(uuid.uuid4()),
            'phone_number': '+233201234567',
            'amount': '500.00',
            'provider_code': 'MTN_GH',
        }
        serializer = CollectRepaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_required_fields(self):
        from apps.api_serializers import CollectRepaymentSerializer

        serializer = CollectRepaymentSerializer(data={})
        self.assertFalse(serializer.is_valid())
        required = ['loan_id', 'phone_number', 'amount', 'provider_code']
        for field in required:
            self.assertIn(field, serializer.errors)


class RequestReportSerializerTests(TestCase):
    """Tests for RequestReportSerializer."""

    def test_valid_report_request(self):
        from apps.api_serializers import RequestReportSerializer

        data = {
            'report_code': 'LOAN_PORTFOLIO',
            'output_format': 'PDF',
        }
        serializer = RequestReportSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_output_format(self):
        from apps.api_serializers import RequestReportSerializer

        data = {
            'report_code': 'LOAN_PORTFOLIO',
            'output_format': 'DOCX',  # not in choices
        }
        serializer = RequestReportSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('output_format', serializer.errors)

    def test_default_parameters(self):
        from apps.api_serializers import RequestReportSerializer

        data = {
            'report_code': 'BOARD_PACK',
            'output_format': 'EXCEL',
        }
        serializer = RequestReportSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['parameters'], {})


class DisburseLoanSerializerTests(TestCase):
    """Tests for DisburseLoanSerializer."""

    def test_valid_disburse_request(self):
        from apps.api_serializers import DisburseLoanSerializer

        data = {
            'loan_id': str(uuid.uuid4()),
            'phone_number': '+260971234567',
            'amount': '2500.00',
            'provider_code': 'AIRTEL_ZM',
        }
        serializer = DisburseLoanSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
