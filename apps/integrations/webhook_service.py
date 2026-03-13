"""
Webhook Delivery System — reliable event notifications with HMAC signatures and retry.
"""
import hashlib
import hmac
import json
import logging
import time

import httpx
from django.utils import timezone
from celery import shared_task
from apps.integrations.models import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)


def trigger_webhook_event(tenant_id, event_type, payload):
    webhooks = Webhook.objects.filter(tenant_id=tenant_id, event_type=event_type, is_active=True)
    for wh in webhooks:
        d = WebhookDelivery.objects.create(webhook=wh, event_type=event_type, payload=payload, status='PENDING')
        deliver_webhook.delay(str(d.id))


@shared_task(name='webhooks.deliver', bind=True, max_retries=3)
def deliver_webhook(self, delivery_id):
    delivery = WebhookDelivery.objects.select_related('webhook').get(id=delivery_id)
    wh = delivery.webhook
    body = json.dumps({'event': delivery.event_type, 'timestamp': timezone.now().isoformat(),
                       'delivery_id': str(delivery.id), 'data': delivery.payload}, default=str)
    sig = hmac.new(wh.secret_hash.encode(), body.encode(), hashlib.sha256).hexdigest()
    headers = {'Content-Type': 'application/json', 'X-Webhook-Signature': f'sha256={sig}',
               'X-Webhook-Event': delivery.event_type, 'User-Agent': 'MFI-Platform/1.0'}
    if wh.headers:
        headers.update(wh.headers)

    start = time.monotonic()
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(wh.target_url, content=body, headers=headers)
        delivery.response_status = r.status_code
        delivery.response_body = r.text[:2000]
        delivery.response_time_ms = int((time.monotonic() - start) * 1000)
        if 200 <= r.status_code < 300:
            delivery.status = 'SUCCESS'
            wh.consecutive_failures = 0
        else:
            delivery.status = 'FAILED'
            wh.consecutive_failures += 1
    except Exception as e:
        delivery.status = 'FAILED'
        delivery.response_body = str(e)[:500]
        wh.consecutive_failures += 1

    wh.last_triggered_at = timezone.now()
    if wh.consecutive_failures >= 10:
        wh.is_active = False
        wh.disabled_at = timezone.now()
    wh.save()
    delivery.save()

    if delivery.status == 'FAILED' and delivery.attempt_number < wh.retry_count:
        retry = WebhookDelivery.objects.create(webhook=wh, event_type=delivery.event_type,
            payload=delivery.payload, attempt_number=delivery.attempt_number + 1, status='PENDING')
        deliver_webhook.apply_async(args=[str(retry.id)], countdown=wh.retry_delay_seconds * delivery.attempt_number)


def notify_loan_created(tid, data): trigger_webhook_event(tid, 'loan.created', data)
def notify_loan_approved(tid, data): trigger_webhook_event(tid, 'loan.approved', data)
def notify_repayment_received(tid, data): trigger_webhook_event(tid, 'repayment.received', data)
def notify_momo_success(tid, data): trigger_webhook_event(tid, 'momo.success', data)
def notify_alert_triggered(tid, data): trigger_webhook_event(tid, 'alert.triggered', data)
