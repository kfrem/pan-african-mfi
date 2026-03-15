"""
Tests for MobileMoneyService.
Tests phone validation, transaction creation, and callback handling.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase


class PhoneValidationTests(TestCase):
    """Tests for MobileMoneyService._validate_phone."""

    def test_valid_phone_passes_regex(self):
        from apps.mobile_money.service import MobileMoneyService

        provider = MagicMock()
        provider.phone_regex = r'^\+233\d{9}$'
        provider.provider_name = 'MTN Ghana'

        # Should not raise
        MobileMoneyService._validate_phone('+233201234567', provider)

    def test_invalid_phone_raises_value_error(self):
        from apps.mobile_money.service import MobileMoneyService

        provider = MagicMock()
        provider.phone_regex = r'^\+233\d{9}$'
        provider.provider_name = 'MTN Ghana'

        with self.assertRaises(ValueError):
            MobileMoneyService._validate_phone('0201234567', provider)

    def test_no_regex_always_passes(self):
        from apps.mobile_money.service import MobileMoneyService

        provider = MagicMock()
        provider.phone_regex = ''  # No regex constraint

        # Should not raise for any format
        MobileMoneyService._validate_phone('any-format-phone', provider)


class HandleCallbackTests(TestCase):
    """Tests for MobileMoneyService.handle_callback."""

    def test_success_callback_updates_status(self):
        from apps.mobile_money.service import MobileMoneyService

        mock_txn = MagicMock()
        mock_txn.status = 'PENDING'
        mock_txn.transaction_type = 'DISBURSEMENT'
        mock_txn.provider_reference = 'TXN-001'

        with patch('apps.mobile_money.service.MobileMoneyTransaction.objects.get',
                   return_value=mock_txn):
            result = MobileMoneyService.handle_callback(
                provider_code='MTN_GH',
                callback_data={
                    'transactionId': 'TXN-001',
                    'status': 'SUCCESS',
                    'description': 'Payment processed',
                }
            )

        self.assertEqual(mock_txn.status, 'SUCCESS')
        mock_txn.save.assert_called_once()

    def test_failed_callback_updates_status(self):
        from apps.mobile_money.service import MobileMoneyService

        mock_txn = MagicMock()
        mock_txn.status = 'PENDING'
        mock_txn.transaction_type = 'COLLECTION'

        with patch('apps.mobile_money.service.MobileMoneyTransaction.objects.get',
                   return_value=mock_txn):
            MobileMoneyService.handle_callback(
                provider_code='MTN_GH',
                callback_data={
                    'transactionId': 'TXN-002',
                    'status': 'FAILED',
                }
            )

        self.assertEqual(mock_txn.status, 'FAILED')

    def test_unknown_transaction_returns_none(self):
        from apps.mobile_money.service import MobileMoneyService
        from apps.mobile_money.models import MobileMoneyTransaction

        with patch('apps.mobile_money.service.MobileMoneyTransaction.objects.get',
                   side_effect=MobileMoneyTransaction.DoesNotExist):
            result = MobileMoneyService.handle_callback(
                provider_code='MTN_GH',
                callback_data={'transactionId': 'NONEXISTENT', 'status': 'SUCCESS'}
            )

        self.assertIsNone(result)

    def test_successful_collection_creates_repayment(self):
        from apps.mobile_money.service import MobileMoneyService

        mock_txn = MagicMock()
        mock_txn.status = 'PENDING'
        mock_txn.transaction_type = 'COLLECTION'
        mock_txn.loan_id = uuid.uuid4()
        mock_txn.amount = Decimal('500.00')

        with patch('apps.mobile_money.service.MobileMoneyTransaction.objects.get',
                   return_value=mock_txn), \
             patch.object(MobileMoneyService, '_auto_create_repayment') as mock_create:
            MobileMoneyService.handle_callback(
                provider_code='MTN_GH',
                callback_data={'transactionId': 'TXN-003', 'status': 'SUCCESS'}
            )
            mock_create.assert_called_once_with(mock_txn)
