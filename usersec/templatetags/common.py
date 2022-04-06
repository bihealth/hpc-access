from importlib import import_module
from django import template
from django.conf import settings

from usersec.models import (
    OBJECT_STATUS_INITIAL,
    OBJECT_STATUS_ACTIVE,
    OBJECT_STATUS_DELETED,
    OBJECT_STATUS_EXPIRED,
    REQUEST_STATUS_INITIAL,
    REQUEST_STATUS_REVISION,
    REQUEST_STATUS_REVISED,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_RETRACTED,
    REQUEST_STATUS_ACTIVE,
)

site = import_module(settings.SITE_PACKAGE)
register = template.Library()


@register.simple_tag
def get_django_setting(name, default=None):
    """
    Return value of Django setting by name or the default value if the setting
    is not found.
    """
    return getattr(settings, name, default)


@register.simple_tag
def site_version():
    """Return the site version"""
    return site.__version__ if hasattr(site, "__version__") else "[UNKNOWN]"


OBJECT_STATUS_COLOR_MAPPING = {
    # Object statuses
    OBJECT_STATUS_INITIAL: "info",
    OBJECT_STATUS_ACTIVE: "success",
    OBJECT_STATUS_DELETED: "muted",
    OBJECT_STATUS_EXPIRED: "warning",
}

REQUEST_STATUS_COLOR_MAPPING = {
    # Request statuses
    REQUEST_STATUS_INITIAL: "info",
    REQUEST_STATUS_ACTIVE: "info",
    REQUEST_STATUS_REVISION: "warning",
    REQUEST_STATUS_REVISED: "info",
    REQUEST_STATUS_APPROVED: "success",
    REQUEST_STATUS_DENIED: "danger",
    REQUEST_STATUS_RETRACTED: "danger",
}


@register.filter
def colorize_request_status(status):
    """Return the color for a given status."""
    return REQUEST_STATUS_COLOR_MAPPING.get(status, "dark")


@register.filter
def colorize_object_status(status):
    """Return the color for a given status."""
    return OBJECT_STATUS_COLOR_MAPPING.get(status, "dark")
