import os

from celery import Celery
from celery.schedules import crontab

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
        "schedule": crontab(hour=0, minute=5),
        # "args": (True, False),
    },
    "send_quota_email_yellow": {
        "task": "adminsec.tasks.send_quota_email_yellow",
        "schedule": crontab(day_of_week=1, hour=0, minute=20),
    },
    "send_quota_email_red": {
        "task": "adminsec.tasks.send_quota_email_red",
        "schedule": crontab(hour=0, minute=10),
    },
    "disable_users_without_consent": {
        "task": "adminsec.tasks.disable_users_without_consent",
        "schedule": crontab(hour=0, minute=15),
    },
}
app.conf.timezone = "UTC"

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
