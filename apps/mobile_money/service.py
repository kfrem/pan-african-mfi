"""
Mobile Money Integration Service — Pan-African Microfinance SaaS
Provider-agnostic: works with any mobile money provider configured
in the mobile_money_providers table. Default integration via Africa's Talking.
"""
import uuid
import logging
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.utils import timezone

from apps.mobile_money.models import (
    MobileMoneyProvider, MobileMoneyTransaction, MobileMoneyReconciliation
)
from apps.clients.models import Client
from apps.loans.models import Loan

logger = logging.getLogger(__name__)


class MobileMoneyService:
    """
    Initiate collections, disbursements, and check transaction status.
    All provider-specific logic is driven by the provider's api_config.
    """

    @classmethod
    def collect_repayment(cls, tenant_id: str, loan_id: str, phone_number: str,
                          amount: Decimal, provider_code: str,
                          initiated_by_id: str, device_id: str = '') -> MobileMoneyTransaction:
        """
        Initiate a mobile money collection (pull payment) for a loan repayment.
        """
        loan = Loan.objects.select_related('client', 'tenant').get(
            id=loan_id, tenant_id=tenant_id)
        provider = MobileMoneyProvider.objects.get(
            provider_code=provider_code,
            country_code=loan.tenant.country_code,
            is_active=True)

        # Validate phone number
        cls._validate_phone(phone_number, provider)

        # Validate amount against provider limits
        if provider.min_transaction and amount < provider.min_transaction:
            raise ValueError(f'Amount below provider minimum ({provider.min_transaction})')
        if provider.max_transaction and amount > provider.max_transaction:
            raise ValueError(f'Amount exceeds provider maximum ({provider.max_transaction})')

        internal_ref = f'COL-{uuid.uuid4().hex[:12].upper()}'

        txn = MobileMoneyTransaction.objects.create(
            tenant_id=tenant_id,
            provider=provider,
            transaction_type='COLLECTION',
            direction='IN',
            phone_number=phone_number,
            amount=amount,
            currency=provider.currency,
            client=loan.client,
            loan=loan,
            internal_reference=internal_ref,
            status='INITIATED',
            initiated_by_id=initiated_by_id,
            device_id=device_id,
        )

        # If online, submit to provider immediately
        if provider.api_type == 'AFRICAS_TALKING':
            cls._submit_africas_talking_collection(txn, provider)
        elif provider.api_type == 'MANUAL':
            # Manual collections stay in INITIATED until confirmed by user
            pass
        else:
            logger.warning(f'Unknown API type: {provider.api_type}')

        return txn

    @classmethod
    def disburse_loan(cls, tenant_id: str, loan_id: str, phone_number: str,
                      amount: Decimal, provider_code: str,
                      initiated_by_id: str) -> MobileMoneyTransaction:
        """
        Disburse a loan via mobile money (push payment).
        """
        loan = Loan.objects.select_related('client', 'tenant').get(
            id=loan_id, tenant_id=tenant_id)
        provider = MobileMoneyProvider.objects.get(
            provider_code=provider_code,
            country_code=loan.tenant.country_code,
            is_active=True)

        cls._validate_phone(phone_number, provider)

        internal_ref = f'DIS-{uuid.uuid4().hex[:12].upper()}'

        txn = MobileMoneyTransaction.objects.create(
            tenant_id=tenant_id,
            provider=provider,
            transaction_type='DISBURSEMENT',
            direction='OUT',
            phone_number=phone_number,
            amount=amount,
            currency=provider.currency,
            client=loan.client,
            loan=loan,
            internal_reference=internal_ref,
            status='INITIATED',
            initiated_by_id=initiated_by_id,
        )

        if provider.api_type == 'AFRICAS_TALKING':
            cls._submit_africas_talking_disbursement(txn, provider)

        return txn

    @classmethod
    def check_status(cls, transaction_id: str) -> MobileMoneyTransaction:
        """Check and update the status of a pending transaction."""
        txn = MobileMoneyTransaction.objects.select_related('provider').get(id=transaction_id)

        if txn.status not in ('INITIATED', 'PENDING'):
            return txn

        if txn.provider.api_type == 'AFRICAS_TALKING':
            cls._check_africas_talking_status(txn)

        return txn

    # ─── AFRICA'S TALKING INTEGRATION ───

    @classmethod
    def _submit_africas_talking_collection(cls, txn: MobileMoneyTransaction,
                                           provider: MobileMoneyProvider):
        """Submit a collection request to Africa's Talking."""
        try:
            import africastalking
            africastalking.initialize(
                settings.AFRICAS_TALKING_USERNAME,
                settings.AFRICAS_TALKING_API_KEY
            )
            payment = africastalking.Payment

            product_name = provider.api_config.get('product_name', 'MoMo')

            response = payment.mobile_checkout(
                product_name=product_name,
                phone_number=txn.phone_number,
                currency_code=txn.currency,
                amount=float(txn.amount),
                metadata={
                    'internal_reference': txn.internal_reference,
                    'loan_id': str(txn.loan_id) if txn.loan_id else '',
                    'tenant_id': str(txn.tenant_id),
                }
            )

            txn.provider_reference = response.get('transactionId', '')
            txn.status = 'PENDING'
            txn.status_message = response.get('description', '')
            txn.save()

        except Exception as e:
            txn.status = 'FAILED'
            txn.status_message = f'API error: {str(e)[:200]}'
            txn.save()
            logger.error(f'AT collection failed for {txn.id}: {e}')

    @classmethod
    def _submit_africas_talking_disbursement(cls, txn: MobileMoneyTransaction,
                                              provider: MobileMoneyProvider):
        """Submit a B2C disbursement via Africa's Talking."""
        try:
            import africastalking
            africastalking.initialize(
                settings.AFRICAS_TALKING_USERNAME,
                settings.AFRICAS_TALKING_API_KEY
            )
            payment = africastalking.Payment

            product_name = provider.api_config.get('product_name', 'MoMo')

            response = payment.mobile_b2c(
                product_name=product_name,
                recipients=[{
                    'phoneNumber': txn.phone_number,
                    'currencyCode': txn.currency,
                    'amount': float(txn.amount),
                    'reason': 'BusinessPayment',
                    'metadata': {
                        'internal_reference': txn.internal_reference,
                        'loan_id': str(txn.loan_id) if txn.loan_id else '',
                    }
                }]
            )

            entries = response.get('entries', [])
            if entries:
                entry = entries[0]
                txn.provider_reference = entry.get('transactionId', '')
                txn.status = 'PENDING'
                txn.status_message = entry.get('status', '')
            else:
                txn.status = 'FAILED'
                txn.status_message = response.get('errorMessage', 'No entries in response')

            txn.save()

        except Exception as e:
            txn.status = 'FAILED'
            txn.status_message = f'API error: {str(e)[:200]}'
            txn.save()
            logger.error(f'AT disbursement failed for {txn.id}: {e}')

    @classmethod
    def _check_africas_talking_status(cls, txn: MobileMoneyTransaction):
        """Check transaction status via callback or polling."""
        # Africa's Talking uses webhooks for status updates.
        # This method is called as a fallback for transactions
        # where the webhook hasn't arrived yet.
        if txn.initiated_at and (timezone.now() - txn.initiated_at).seconds > 300:
            txn.status = 'TIMEOUT'
            txn.status_message = 'No callback received within 5 minutes'
            txn.save()

    # ─── CALLBACK HANDLER ───

    @classmethod
    def handle_callback(cls, provider_code: str, callback_data: dict) -> Optional[MobileMoneyTransaction]:
        """
        Handle mobile money provider callback (webhook).
        Called from the webhook endpoint when AT sends a payment notification.
        """
        provider_ref = callback_data.get('transactionId', '')
        status_text = callback_data.get('status', '').upper()

        try:
            txn = MobileMoneyTransaction.objects.get(
                provider_reference=provider_ref,
                provider__provider_code=provider_code
            )
        except MobileMoneyTransaction.DoesNotExist:
            logger.warning(f'Callback for unknown transaction: {provider_ref}')
            return None

        if status_text in ('SUCCESS', 'SUCCESSFUL'):
            txn.status = 'SUCCESS'
            txn.completed_at = timezone.now()

            # If this is a collection, auto-create a repayment record
            if txn.transaction_type == 'COLLECTION' and txn.loan_id:
                cls._auto_create_repayment(txn)

        elif status_text in ('FAILED', 'REJECTED'):
            txn.status = 'FAILED'
        else:
            txn.status_message = f'Unknown callback status: {status_text}'

        txn.status_message = callback_data.get('description', txn.status_message)
        txn.save()
        return txn

    @classmethod
    def _auto_create_repayment(cls, txn: MobileMoneyTransaction):
        """Auto-create a repayment record from a successful mobile money collection."""
        from apps.loans.models import Repayment

        if Repayment.objects.filter(
            tenant_id=txn.tenant_id,
            loan_id=txn.loan_id,
            payment_reference=txn.internal_reference
        ).exists():
            return  # Already created

        loan = txn.loan
        schedule = loan.schedule.filter(
            status__in=['PENDING', 'PARTIAL', 'OVERDUE']
        ).order_by('instalment_number').first()

        # Split amount
        if schedule:
            interest_remaining = schedule.interest_due - schedule.interest_paid
            interest_applied = min(txn.amount, interest_remaining)
            principal_applied = txn.amount - interest_applied
        else:
            interest_applied = Decimal('0')
            principal_applied = txn.amount

        count = Repayment.objects.filter(tenant_id=txn.tenant_id).count() + 1
        receipt = f'RCP-MOMO-{timezone.now().strftime("%Y%m%d")}-{count:06d}'

        repayment = Repayment.objects.create(
            tenant_id=txn.tenant_id,
            loan=loan,
            schedule=schedule,
            amount=txn.amount,
            currency=txn.currency,
            payment_method='MOBILE_MONEY',
            payment_reference=txn.internal_reference,
            received_by_id=txn.initiated_by_id,
            received_at=txn.completed_at or timezone.now(),
            principal_applied=principal_applied,
            interest_applied=interest_applied,
            receipt_number=receipt,
            sync_status='SYNCED',
        )

        # Update schedule and loan balances
        if schedule:
            schedule.principal_paid += principal_applied
            schedule.interest_paid += interest_applied
            schedule.total_paid += txn.amount
            if schedule.total_paid >= schedule.total_due:
                schedule.status = 'PAID'
                schedule.paid_date = timezone.now().date()
            else:
                schedule.status = 'PARTIAL'
            schedule.save()

        loan.outstanding_principal = max(loan.outstanding_principal - principal_applied, Decimal('0'))
        if loan.outstanding_principal <= 0:
            loan.status = 'CLOSED'
            loan.closed_date = timezone.now().date()
        loan.save()

        # Link repayment to the momo transaction
        txn.repayment = repayment
        txn.save(update_fields=['repayment'])

    # ─── VALIDATION ───

    @staticmethod
    def _validate_phone(phone_number: str, provider: MobileMoneyProvider):
        """Validate phone number format for the provider."""
        import re
        if provider.phone_regex:
            if not re.match(provider.phone_regex, phone_number):
                raise ValueError(
                    f'Invalid phone number format for {provider.provider_name}. '
                    f'Expected format matching: {provider.phone_regex}'
                )
