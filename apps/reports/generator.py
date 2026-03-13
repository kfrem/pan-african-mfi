"""
PDF Report Generator — Pan-African Microfinance SaaS
Generates branded, professional PDF reports using WeasyPrint.
All reports include institution branding, page numbers, and confidentiality notices.
"""
import io
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from apps.tenants.models import Tenant
from apps.reports.models import ReportRun
from apps.loans.models import Loan, RepaymentSchedule
from apps.investors.models import InvestorProfile

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Base report generator. All reports inherit common branding and structure.
    """

    def __init__(self, tenant_id: str, generated_by_id: str = None):
        self.tenant = Tenant.objects.select_related('country', 'licence_tier').get(id=tenant_id)
        self.generated_by_id = generated_by_id
        self.now = timezone.now()

    @property
    def brand_context(self) -> dict:
        """Common branding context for all report templates."""
        return {
            'institution_name': self.tenant.trading_name or self.tenant.name,
            'logo_url': self.tenant.logo_url,
            'primary_colour': self.tenant.primary_brand_colour or '#1b3a6b',
            'secondary_colour': self.tenant.secondary_brand_colour or '#2563eb',
            'currency': self.tenant.default_currency,
            'country': self.tenant.country.country_name,
            'generated_at': self.now.strftime('%d %B %Y, %H:%M UTC'),
            'generated_date': self.now.strftime('%d/%m/%Y'),
            'confidentiality': 'CONFIDENTIAL — For authorised recipients only',
            'page_footer': f'{self.tenant.trading_name or self.tenant.name} · Generated {self.now.strftime("%d/%m/%Y %H:%M")} · Page',
        }

    def generate_html(self, template_name: str, context: dict) -> str:
        """Render report HTML from template + context."""
        full_context = {**self.brand_context, **context}
        return render_to_string(f'reports/{template_name}', full_context)

    def generate_pdf(self, html_content: str) -> bytes:
        """Convert HTML to PDF bytes."""
        pdf = HTML(string=html_content).write_pdf()
        return pdf

    def save_report(self, report_run_id: str, pdf_bytes: bytes) -> str:
        """Save PDF to Supabase Storage and update the report run record."""
        from supabase import create_client
        from django.conf import settings

        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        filename = f'reports/{self.tenant.id}/{report_run_id}.pdf'
        sb.storage.from_('reports').upload(filename, pdf_bytes, {
            'content-type': 'application/pdf'
        })

        # Update report run
        run = ReportRun.objects.get(id=report_run_id)
        run.file_path = filename
        run.file_size_bytes = len(pdf_bytes)
        run.status = 'COMPLETED'
        run.generated_at = self.now
        run.save()

        return filename


class InvestorReportGenerator(ReportGenerator):
    """Generate branded investor report PDF."""

    def generate(self, investor_id: str, period: str = None) -> bytes:
        investor = InvestorProfile.objects.select_related('user').get(
            id=investor_id, tenant=self.tenant)

        active_loans = Loan.objects.filter(
            tenant=self.tenant, status__in=['ACTIVE', 'DISBURSED']
        )

        from django.db.models import Sum, Count, Q, Avg
        portfolio = active_loans.aggregate(
            total=Sum('outstanding_principal'),
            count=Count('id'),
            avg_rate=Avg('interest_rate_pct'),
        )
        par30 = active_loans.filter(days_past_due__gte=30).aggregate(
            total=Sum('outstanding_principal'))['total'] or Decimal('0')
        par30_pct = (par30 / portfolio['total'] * 100) if portfolio['total'] else Decimal('0')

        context = {
            'report_title': 'Investor Report',
            'period': period or self.now.strftime('%B %Y'),
            'investor_name': investor.investor_name,
            'investor_type': investor.investor_type,
            'investment_currency': investor.investment_currency,
            'invested_amount': investor.invested_amount,
            'investment_date': investor.investment_date.strftime('%d %B %Y'),
            'total_portfolio': portfolio['total'] or Decimal('0'),
            'active_loans': portfolio['count'] or 0,
            'avg_interest_rate': portfolio['avg_rate'] or Decimal('0'),
            'par30_pct': par30_pct,
            'par30_amount': par30,
            # Add more metrics as needed
        }

        html = self.generate_html('investor_report.html', context)
        return self.generate_pdf(html)


class BoardPackGenerator(ReportGenerator):
    """Generate the full board pack PDF combining all governance metrics."""

    def generate(self, period: str = None) -> bytes:
        from apps.tenants.country_pack_engine import CountryPackEngine

        engine = CountryPackEngine.for_tenant(str(self.tenant.id))

        active_loans = Loan.objects.filter(
            tenant=self.tenant, status__in=['ACTIVE', 'DISBURSED']
        )
        from django.db.models import Sum, Count, Q

        portfolio_total = active_loans.aggregate(t=Sum('outstanding_principal'))['t'] or Decimal('0')
        par30 = active_loans.filter(days_past_due__gte=30).aggregate(
            t=Sum('outstanding_principal'))['t'] or Decimal('0')
        par90 = active_loans.filter(days_past_due__gte=90).aggregate(
            t=Sum('outstanding_principal'))['t'] or Decimal('0')

        insider_loans = active_loans.filter(is_insider_loan=True)
        insider_total = insider_loans.aggregate(t=Sum('outstanding_principal'))['t'] or Decimal('0')

        # Classification breakdown
        classifications = {}
        for cls in ['CURRENT', 'WATCH', 'SUBSTANDARD', 'DOUBTFUL', 'LOSS']:
            amt = active_loans.filter(classification=cls).aggregate(
                t=Sum('outstanding_principal'))['t'] or Decimal('0')
            classifications[cls] = {
                'amount': amt,
                'pct': (amt / portfolio_total * 100) if portfolio_total else Decimal('0'),
                'count': active_loans.filter(classification=cls).count(),
            }

        context = {
            'report_title': 'Board Pack',
            'period': period or self.now.strftime('%B %Y'),
            'portfolio_total': portfolio_total,
            'active_loans_count': active_loans.count(),
            'par30_pct': (par30 / portfolio_total * 100) if portfolio_total else Decimal('0'),
            'par30_amount': par30,
            'par90_pct': (par90 / portfolio_total * 100) if portfolio_total else Decimal('0'),
            'par90_amount': par90,
            'classifications': classifications,
            'car_requirement': engine.car_requirement,
            'insider_total': insider_total,
            'insider_limit_pct': engine.insider_lending_limit_pct,
            'insider_loans': list(insider_loans.values(
                'loan_number', 'client__full_legal_name', 'outstanding_principal',
                'client__insider_relationship'
            )[:20]),
        }

        html = self.generate_html('board_pack.html', context)
        return self.generate_pdf(html)


class LoanStatementGenerator(ReportGenerator):
    """Generate individual loan statement for a client."""

    def generate(self, loan_id: str) -> bytes:
        loan = Loan.objects.select_related(
            'client', 'product', 'loan_officer', 'branch'
        ).get(id=loan_id, tenant=self.tenant)

        schedule = RepaymentSchedule.objects.filter(
            loan=loan
        ).order_by('instalment_number')

        from apps.loans.models import Repayment
        repayments = Repayment.objects.filter(
            loan=loan, reversed=False
        ).order_by('received_at')

        total_paid = repayments.aggregate(t=Sum('amount'))['t'] or Decimal('0')

        context = {
            'report_title': 'Loan Statement',
            'loan': loan,
            'client': loan.client,
            'schedule': list(schedule.values(
                'instalment_number', 'due_date', 'principal_due', 'interest_due',
                'total_due', 'total_paid', 'status', 'days_late'
            )),
            'repayments': list(repayments.values(
                'received_at', 'amount', 'payment_method', 'receipt_number',
                'principal_applied', 'interest_applied'
            )),
            'total_paid': total_paid,
            'remaining_balance': loan.outstanding_principal,
        }

        html = self.generate_html('loan_statement.html', context)
        return self.generate_pdf(html)
