"""
USSD Session Handler — Pan-African Microfinance SaaS
Provides borrower self-service on feature phones via Africa's Talking USSD.

Menu Structure:
1. Check loan balance
2. Next payment due
3. Recent transactions
4. Contact my officer

Accessed via service code (e.g. *384*123#)
"""
import logging
from datetime import date
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.clients.models import Client
from apps.loans.models import Loan, RepaymentSchedule, Repayment
from apps.notifications.models import UssdSession

logger = logging.getLogger(__name__)

MAIN_MENU = (
    "CON Welcome to {institution}\n"
    "1. Check loan balance\n"
    "2. Next payment due\n"
    "3. Recent payments\n"
    "4. Contact my officer\n"
    "0. Exit"
)


@csrf_exempt
@require_POST
def ussd_callback(request):
    """
    Africa's Talking USSD callback endpoint.
    POST /api/v1/ussd/callback

    AT sends: sessionId, serviceCode, phoneNumber, text (user input history separated by *)
    We return: CON (continue) or END (terminate) + response text
    """
    session_id = request.POST.get('sessionId', '')
    service_code = request.POST.get('serviceCode', '')
    phone = request.POST.get('phoneNumber', '')
    text = request.POST.get('text', '')

    # Parse input chain: AT sends cumulative input separated by *
    # e.g. "" (initial), "1" (selected option 1), "1*1" (option 1 then sub-option 1)
    inputs = text.split('*') if text else []
    level = len(inputs)

    # Look up client by phone
    client = _find_client(phone)

    # Track session
    session, _ = UssdSession.objects.get_or_create(
        session_id=session_id,
        defaults={
            'phone_number': phone,
            'service_code': service_code,
            'client_id': client.id if client else None,
            'tenant_id': client.tenant_id if client else None,
            'status': 'ACTIVE',
        }
    )
    session.current_level = level
    session.last_input = text
    session.save(update_fields=['current_level', 'last_input'])

    # Route
    try:
        if not client:
            response = "END Sorry, this phone number is not registered. Please contact your microfinance institution."
        elif level == 0:
            institution = client.tenant.trading_name or client.tenant.name
            response = MAIN_MENU.format(institution=institution)
        elif inputs[0] == '1':
            response = _handle_balance(client)
        elif inputs[0] == '2':
            response = _handle_next_payment(client)
        elif inputs[0] == '3':
            response = _handle_recent_payments(client)
        elif inputs[0] == '4':
            response = _handle_contact_officer(client)
        elif inputs[0] == '0':
            response = "END Thank you for using our service. Goodbye."
        else:
            response = "END Invalid option. Please try again."

    except Exception as e:
        logger.error(f"USSD error for {phone}: {e}")
        response = "END An error occurred. Please try again later."

    # Update session status
    if response.startswith('END'):
        session.status = 'COMPLETED'
        session.ended_at = date.today()
        session.save(update_fields=['status', 'ended_at'])

    return HttpResponse(response, content_type='text/plain')


def _find_client(phone: str) -> Client | None:
    """Find client by phone number (tries primary and secondary)."""
    # Normalise phone: remove spaces, ensure + prefix
    clean = phone.replace(' ', '').replace('-', '')
    if not clean.startswith('+'):
        clean = '+' + clean

    client = Client.objects.filter(
        phone_primary=clean, deleted_at__isnull=True
    ).select_related('tenant', 'assigned_officer').first()

    if not client:
        # Try without + prefix or with different formats
        variants = [clean, clean.lstrip('+'), '0' + clean[-9:]]
        for v in variants:
            client = Client.objects.filter(
                phone_primary__endswith=v[-9:], deleted_at__isnull=True
            ).select_related('tenant', 'assigned_officer').first()
            if client:
                break

    return client


def _handle_balance(client: Client) -> str:
    """Show all active loan balances."""
    loans = Loan.objects.filter(
        client=client, tenant=client.tenant,
        status__in=['ACTIVE', 'DISBURSED']
    ).order_by('-disbursement_date')

    if not loans.exists():
        return "END You have no active loans."

    lines = [f"CON Your loan balances ({client.tenant.default_currency}):"]
    for loan in loans[:3]:  # Max 3 loans to fit USSD screen
        lines.append(f"  {loan.loan_number}: {loan.outstanding_principal:,.0f}")

    if loans.count() > 3:
        lines.append(f"  ...and {loans.count() - 3} more")

    lines.append("\n0. Back to menu")
    return "\n".join(lines)


def _handle_next_payment(client: Client) -> str:
    """Show next payment due date and amount."""
    next_due = RepaymentSchedule.objects.filter(
        loan__client=client,
        loan__tenant=client.tenant,
        loan__status__in=['ACTIVE', 'DISBURSED'],
        status__in=['PENDING', 'PARTIAL', 'OVERDUE'],
    ).order_by('due_date').first()

    if not next_due:
        return "END No payments currently due."

    currency = next_due.loan.currency
    remaining = next_due.total_due - next_due.total_paid
    overdue_text = " (OVERDUE)" if next_due.status == 'OVERDUE' else ""

    return (
        f"END Next payment:\n"
        f"Loan: {next_due.loan.loan_number}\n"
        f"Due: {next_due.due_date.strftime('%d/%m/%Y')}{overdue_text}\n"
        f"Amount: {currency} {remaining:,.0f}"
    )


def _handle_recent_payments(client: Client) -> str:
    """Show last 3 repayments."""
    repayments = Repayment.objects.filter(
        loan__client=client,
        loan__tenant=client.tenant,
        reversed=False,
    ).order_by('-received_at')[:3]

    if not repayments.exists():
        return "END No recent payments found."

    lines = ["END Recent payments:"]
    for r in repayments:
        dt = r.received_at.strftime('%d/%m')
        method = 'MoMo' if r.payment_method == 'MOBILE_MONEY' else r.payment_method.title()
        lines.append(f"  {dt}: {r.currency} {r.amount:,.0f} ({method})")

    return "\n".join(lines)


def _handle_contact_officer(client: Client) -> str:
    """Show assigned loan officer contact details."""
    officer = client.assigned_officer
    if not officer:
        institution = client.tenant.trading_name or client.tenant.name
        return f"END Please contact {institution} directly for assistance."

    return (
        f"END Your loan officer:\n"
        f"Name: {officer.full_name}\n"
        f"Phone: {officer.phone or 'Not available'}\n"
        f"Email: {officer.email}"
    )
