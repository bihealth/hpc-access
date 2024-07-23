import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("hpcaccess")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


app.conf.beat_schedule = {
    "sync_ldap": {
        "task": "adminsec.tasks.sync_ldap",
        "schedule": crontab(
            hour=settings.CRON_SYNC_LDAP_HOUR, minute=settings.CRON_SYNC_LDAP_MINUTE
        ),
        # "args": (True, False),
    },
    "send_quota_email_yellow": {
        "task": "adminsec.tasks.send_quota_email_yellow",
        "schedule": crontab(
            day_of_week=settings.CRON_QUOTA_EMAIL_YELLOW_DOW,
            hour=settings.CRON_QUOTA_EMAIL_YELLOW_HOUR,
            minute=settings.CRON_QUOTA_EMAIL_YELLOW_MINUTE,
        ),
    },
    "send_quota_email_red": {
        "task": "adminsec.tasks.send_quota_email_red",
        "schedule": crontab(
            hour=settings.CRON_QUOTA_EMAIL_RED_HOUR, minute=settings.CRON_QUOTA_EMAIL_RED_MINUTE
        ),
    },
    "disable_users_without_consent": {
        "task": "adminsec.tasks.disable_users_without_consent",
        "schedule": crontab(
            hour=settings.CRON_DISABLE_USERS_HOUR, minute=settings.CRON_DISABLE_USERS_MINUTE
        ),
    },
}
app.conf.timezone = "UTC"

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
