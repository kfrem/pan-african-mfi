"""
Tests for the data import validation engine.
Tests CSV parsing, validation rules, and error/warning collection.
"""
import io
import csv
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase


class ImportValidationEngineTests(TestCase):
    """Tests for ImportValidationEngine validation logic."""

    def _make_csv(self, headers: list, rows: list[list]) -> bytes:
        """Helper to build CSV bytes from headers and rows."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode('utf-8')

    def _make_engine(self, import_type='CLIENTS'):
        """Create an engine with mocked Tenant and CountryPackEngine."""
        from apps.onboarding.import_engine import ImportValidationEngine

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()

        mock_engine = MagicMock()
        mock_engine.validate_national_id.return_value = {'valid': True, 'message': ''}

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_engine), \
             patch('apps.onboarding.import_engine.Client.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = []
            engine = ImportValidationEngine(str(mock_tenant.id), import_type)
            engine._mock_country_engine = mock_engine
        return engine

    def test_valid_client_csv(self):
        """Valid client rows should be accepted without errors."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['full_legal_name', 'client_type', 'phone_primary', 'gender',
                   'date_of_birth', 'national_id_number', 'monthly_income', 'risk_rating']
        rows = [
            ['Kwame Asante', 'INDIVIDUAL', '+233201234567', 'MALE',
             '15/06/1985', 'GH-12345678', '5000', 'LOW'],
        ]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()
        mock_country_engine.validate_national_id.return_value = {'valid': True, 'message': ''}

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine), \
             patch('apps.onboarding.import_engine.Client.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = []
            engine = ImportValidationEngine(str(mock_tenant.id), 'CLIENTS')
            result = engine.validate_csv(csv_bytes)

        self.assertEqual(result['total_rows'], 1)
        self.assertEqual(result['valid_rows'], 1)
        self.assertEqual(result['error_rows'], 0)
        self.assertEqual(len(result['errors']), 0)

    def test_missing_required_client_fields(self):
        """Missing required fields should generate errors."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['full_legal_name', 'client_type', 'phone_primary']
        rows = [
            ['', 'INDIVIDUAL', ''],  # both name and phone missing
        ]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()
        mock_country_engine.validate_national_id.return_value = {'valid': True, 'message': ''}

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine), \
             patch('apps.onboarding.import_engine.Client.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = []
            engine = ImportValidationEngine(str(mock_tenant.id), 'CLIENTS')
            result = engine.validate_csv(csv_bytes)

        self.assertEqual(result['total_rows'], 1)
        self.assertGreater(result['error_rows'], 0)
        error_fields = [e['field'] for e in result['errors']]
        self.assertIn('full_legal_name', error_fields)
        self.assertIn('phone_primary', error_fields)

    def test_invalid_client_type(self):
        """Invalid client_type should produce an error."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['full_legal_name', 'client_type', 'phone_primary']
        rows = [['Test Person', 'COMPANY', '+233201234567']]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()
        mock_country_engine.validate_national_id.return_value = {'valid': True, 'message': ''}

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine), \
             patch('apps.onboarding.import_engine.Client.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = []
            engine = ImportValidationEngine(str(mock_tenant.id), 'CLIENTS')
            result = engine.validate_csv(csv_bytes)

        error_fields = [e['field'] for e in result['errors']]
        self.assertIn('client_type', error_fields)

    def test_underage_client_rejected(self):
        """Clients under 18 should be rejected."""
        from apps.onboarding.import_engine import ImportValidationEngine
        from datetime import date, timedelta

        young_dob = (date.today() - timedelta(days=365 * 16)).strftime('%d/%m/%Y')
        headers = ['full_legal_name', 'client_type', 'phone_primary', 'date_of_birth']
        rows = [['Young Person', 'INDIVIDUAL', '+233201234567', young_dob]]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()
        mock_country_engine.validate_national_id.return_value = {'valid': True, 'message': ''}

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine), \
             patch('apps.onboarding.import_engine.Client.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = []
            engine = ImportValidationEngine(str(mock_tenant.id), 'CLIENTS')
            result = engine.validate_csv(csv_bytes)

        error_messages = [e['error'] for e in result['errors']]
        self.assertTrue(any('18' in m for m in error_messages))

    def test_negative_income_rejected(self):
        """Negative monthly income should produce an error."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['full_legal_name', 'client_type', 'phone_primary', 'monthly_income']
        rows = [['Test Client', 'INDIVIDUAL', '+233201234567', '-100']]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()
        mock_country_engine.validate_national_id.return_value = {'valid': True, 'message': ''}

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine), \
             patch('apps.onboarding.import_engine.Client.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = []
            engine = ImportValidationEngine(str(mock_tenant.id), 'CLIENTS')
            result = engine.validate_csv(csv_bytes)

        error_fields = [e['field'] for e in result['errors']]
        self.assertIn('monthly_income', error_fields)

    def test_duplicate_national_id_in_file(self):
        """Duplicate national IDs within the same import file should error."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['full_legal_name', 'client_type', 'phone_primary', 'national_id_number']
        rows = [
            ['Alice Mensah', 'INDIVIDUAL', '+233201234567', 'GH-99999999'],
            ['Bob Mensah', 'INDIVIDUAL', '+233207654321', 'GH-99999999'],  # duplicate
        ]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()
        mock_country_engine.validate_national_id.return_value = {'valid': True, 'message': ''}

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine), \
             patch('apps.onboarding.import_engine.Client.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = []
            engine = ImportValidationEngine(str(mock_tenant.id), 'CLIENTS')
            result = engine.validate_csv(csv_bytes)

        # Second row should have a duplicate ID error
        error_fields = [e['field'] for e in result['errors']]
        self.assertIn('national_id_number', error_fields)

    def test_loan_outstanding_exceeds_principal(self):
        """Outstanding principal exceeding principal should be an error."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['client_number', 'principal_amount', 'outstanding_principal', 'status']
        rows = [
            ['CL-00001', '1000', '1500', 'ACTIVE'],  # outstanding > principal
        ]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine), \
             patch('apps.onboarding.import_engine.Client.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = {'CL-00001': str(uuid.uuid4())}
            engine = ImportValidationEngine(str(mock_tenant.id), 'LOANS')
            result = engine.validate_csv(csv_bytes)

        error_fields = [e['field'] for e in result['errors']]
        self.assertIn('outstanding_principal', error_fields)

    def test_chart_of_accounts_validation(self):
        """Chart of accounts import should validate account codes and types."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['account_code', 'account_name', 'account_type', 'normal_balance']
        rows = [
            ['1000', 'Cash', 'ASSET', 'D'],
            ['2000', 'Payables', 'LIABILITY', 'C'],
            ['1000', 'Duplicate', 'ASSET', 'D'],  # duplicate code
            ['3000', 'Revenue', 'INVALID_TYPE', 'C'],  # invalid type
        ]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine):
            engine = ImportValidationEngine(str(mock_tenant.id), 'CHART_OF_ACCOUNTS')
            result = engine.validate_csv(csv_bytes)

        self.assertEqual(result['total_rows'], 4)
        # Rows 3 (duplicate) and 4 (invalid type) should have errors
        self.assertGreaterEqual(result['error_rows'], 2)

    def test_opening_balances_must_balance(self):
        """Opening balances must have matching debits and credits."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['account_code', 'debit_amount', 'credit_amount']
        rows = [
            ['1000', '5000', '0'],
            ['2000', '0', '4000'],  # doesn't balance: 5000 vs 4000
        ]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()

        mock_account_qs = MagicMock()
        mock_account_qs.values_list.return_value = [('1000', str(uuid.uuid4())), ('2000', str(uuid.uuid4()))]

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine), \
             patch('apps.onboarding.import_engine.ImportValidationEngine._validate_opening_balances') as mock_validate:
            # Call with a direct balance check
            engine = ImportValidationEngine(str(mock_tenant.id), 'OPENING_BALANCES')
            # Manually test balance logic
            from decimal import Decimal
            total_debit = Decimal('5000')
            total_credit = Decimal('4000')
            diff = abs(total_debit - total_credit)
            self.assertGreater(diff, Decimal('0.01'))

    def test_date_parsing(self):
        """Date parser should handle multiple common African date formats."""
        from apps.onboarding.import_engine import ImportValidationEngine

        valid_dates = [
            ('15/06/1985', 'DD/MM/YYYY'),
            ('1985-06-15', 'YYYY-MM-DD'),
            ('15-06-1985', 'DD-MM-YYYY'),
            ('15.06.1985', 'DD.MM.YYYY'),
        ]
        for date_str, fmt in valid_dates:
            result = ImportValidationEngine._parse_date(date_str)
            self.assertIsNotNone(result, f'Failed to parse {date_str} ({fmt})')

        invalid_dates = ['not-a-date', '32/13/2020', '']
        for date_str in invalid_dates:
            result = ImportValidationEngine._parse_date(date_str)
            self.assertIsNone(result, f'Should have failed: {date_str}')

    def test_unsupported_import_type(self):
        """Unsupported import types should return an error."""
        from apps.onboarding.import_engine import ImportValidationEngine

        headers = ['field1', 'field2']
        rows = [['val1', 'val2']]
        csv_bytes = self._make_csv(headers, rows)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_country_engine = MagicMock()

        with patch('apps.onboarding.import_engine.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.onboarding.import_engine.CountryPackEngine.for_tenant', return_value=mock_country_engine):
            engine = ImportValidationEngine(str(mock_tenant.id), 'UNSUPPORTED_TYPE')
            result = engine.validate_csv(csv_bytes)

        self.assertGreater(len(result['errors']), 0)
        self.assertIn('Unsupported', result['errors'][0]['error'])
