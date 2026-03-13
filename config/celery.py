import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('microfinance_saas')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(['apps'])

# ─── BEAT SCHEDULE ───
# These run automatically. Additional schedules can be configured
# per tenant via django-celery-beat in the admin.

app.conf.beat_schedule = {
    'reclassify-loans-nightly': {
        'task': 'loans.reclassify_all',
        'schedule': crontab(hour=1, minute=0),
    },
    'send-repayment-reminders': {
        'task': 'sms.send_repayment_reminders',
        'schedule': crontab(hour=2, minute=0),
    },
    'run-aml-monitoring': {
        'task': 'aml.run_monitoring',
        'schedule': crontab(hour=3, minute=0),
    },
    'escalate-stale-aml-alerts': {
        'task': 'aml.escalate_stale_alerts',
        'schedule': crontab(hour=4, minute=0),
    },
    'process-sync-queue': {
        'task': 'sync.process_queue',
        'schedule': 300.0,  # Every 5 minutes
    },
    'check-scheduled-reports': {
        'task': 'reports.check_scheduled',
        'schedule': 3600.0,  # Every hour
    },
    'send-kyc-expiry-warnings': {
        'task': 'kyc.send_expiry_warnings',
        'schedule': crontab(hour=6, minute=0),
    },
    'check-notification-thresholds': {
        'task': 'notifications.check_thresholds',
        'schedule': crontab(hour=7, minute=0),
    },
}
