"""
Tests for report generation helpers.
Tests context building, date parsing, and format generation.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase


class ReportContextTests(TestCase):
    """Tests for _get_report_context helper in tasks.py."""

    def _make_mock_run(self, report_code='BOARD_PACK', params=None):
        run = MagicMock()
        run.tenant_id = uuid.uuid4()
        run.parameters = params or {}
        run.report.report_code = report_code
        run.report.report_name = 'Test Report'
        run.output_format = 'PDF'
        return run

    def test_context_includes_required_keys(self):
        from apps.tasks import _get_report_context

        mock_tenant = MagicMock()
        mock_tenant.name = 'Test MFI'
        mock_tenant.primary_brand_colour = '#1a56db'
        mock_tenant.default_currency = 'GHS'

        mock_loan_qs = MagicMock()
        mock_loan_qs.aggregate.side_effect = [
            {'total_portfolio': Decimal('5000000'), 'total_loans': 1247, 'avg_rate': Decimal('24.5')},
            {'par30_balance': Decimal('162000')},
        ]

        run = self._make_mock_run()

        with patch('apps.tasks.Tenant.objects.select_related') as mock_sel:
            mock_sel.return_value.get.return_value = mock_tenant
            with patch('apps.tasks.Loan.objects.filter', return_value=mock_loan_qs):
                ctx = _get_report_context(run)

        required_keys = ['institution_name', 'primary_colour', 'currency',
                         'generated_date', 'total_portfolio', 'active_loans', 'par30_pct']
        for key in required_keys:
            self.assertIn(key, ctx, f'Missing key: {key}')

    def test_par30_pct_calculation(self):
        from apps.tasks import _get_report_context

        mock_tenant = MagicMock()
        mock_tenant.name = 'Test MFI'
        mock_tenant.primary_brand_colour = '#000'
        mock_tenant.default_currency = 'ZMW'

        mock_loan_qs = MagicMock()
        mock_loan_qs.aggregate.side_effect = [
            {'total_portfolio': Decimal('1000000'), 'total_loans': 100, 'avg_rate': Decimal('20')},
            {'par30_balance': Decimal('30000')},
        ]

        run = self._make_mock_run()

        with patch('apps.tasks.Tenant.objects.select_related') as mock_sel:
            mock_sel.return_value.get.return_value = mock_tenant
            with patch('apps.tasks.Loan.objects.filter', return_value=mock_loan_qs):
                ctx = _get_report_context(run)

        # 30000 / 1000000 * 100 = 3.0%
        self.assertAlmostEqual(ctx['par30_pct'], 3.0, places=1)

    def test_zero_portfolio_handles_gracefully(self):
        from apps.tasks import _get_report_context

        mock_tenant = MagicMock()
        mock_tenant.name = 'New MFI'
        mock_tenant.primary_brand_colour = '#000'
        mock_tenant.default_currency = 'GHS'

        mock_loan_qs = MagicMock()
        mock_loan_qs.aggregate.side_effect = [
            {'total_portfolio': None, 'total_loans': 0, 'avg_rate': None},
            {'par30_balance': None},
        ]

        run = self._make_mock_run()

        with patch('apps.tasks.Tenant.objects.select_related') as mock_sel:
            mock_sel.return_value.get.return_value = mock_tenant
            with patch('apps.tasks.Loan.objects.filter', return_value=mock_loan_qs):
                ctx = _get_report_context(run)

        self.assertEqual(ctx['par30_pct'], 0.0)
        self.assertEqual(ctx['active_loans'], 0)


class ReportFormatTests(TestCase):
    """Tests for format-specific generation helpers."""

    def _make_mock_run(self, output_format='PDF', report_code='BOARD_PACK'):
        run = MagicMock()
        run.tenant_id = uuid.uuid4()
        run.parameters = {}
        run.report.report_code = report_code
        run.report.report_name = 'Test Report'
        run.output_format = output_format
        run.id = uuid.uuid4()
        return run

    def test_placeholder_pdf_returns_storage_path(self):
        from apps.tasks import _generate_placeholder_pdf

        run = self._make_mock_run('PDF')
        file_path, page_count = _generate_placeholder_pdf(run)

        self.assertIn(str(run.tenant_id), file_path)
        self.assertIn('.pdf', file_path)
        self.assertEqual(page_count, 1)

    def test_csv_report_returns_correct_format(self):
        from apps.tasks import _generate_csv_report

        mock_tenant = MagicMock()
        mock_tenant.name = 'Test MFI'
        mock_tenant.default_currency = 'GHS'

        run = self._make_mock_run('CSV', 'LOAN_PORTFOLIO')

        mock_loan_qs = MagicMock()
        mock_loan_qs.__iter__ = MagicMock(return_value=iter([]))

        with patch('apps.tasks.Tenant.objects.get', return_value=mock_tenant), \
             patch('apps.tasks.Loan.objects.filter', return_value=mock_loan_qs):
            file_path, page_count = _generate_csv_report(run)

        self.assertIn(str(run.tenant_id), file_path)
        self.assertIn('.csv', file_path)
        self.assertEqual(page_count, 1)

    def test_excel_report_without_openpyxl_fallback(self):
        """If openpyxl is not importable, should still return a valid path."""
        from apps.tasks import _generate_excel_report

        run = self._make_mock_run('EXCEL', 'GENERIC_REPORT')

        # Mock openpyxl as not available
        with patch.dict('sys.modules', {'openpyxl': None}):
            file_path, page_count = _generate_excel_report(run)

        self.assertIn('.xlsx', file_path)
