from importlib import import_module

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from adminsec.constants import POSIX_AG_PREFIX, POSIX_PROJECT_PREFIX
from usersec.models import (
    OBJECT_STATUS_ACTIVE,
    OBJECT_STATUS_DELETED,
    OBJECT_STATUS_EXPIRED,
    OBJECT_STATUS_INITIAL,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_INITIAL,
    REQUEST_STATUS_RETRACTED,
    REQUEST_STATUS_REVISED,
    REQUEST_STATUS_REVISION,
    HpcQuotaStatus,
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
    OBJECT_STATUS_INITIAL: "secondary",
    OBJECT_STATUS_ACTIVE: "success",
    OBJECT_STATUS_DELETED: "muted",
    OBJECT_STATUS_EXPIRED: "warning",
}

REQUEST_STATUS_COLOR_MAPPING = {
    # Request statuses
    REQUEST_STATUS_INITIAL: "secondary",
    REQUEST_STATUS_ACTIVE: "secondary",
    REQUEST_STATUS_REVISION: "warning",
    REQUEST_STATUS_REVISED: "secondary",
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


@register.filter
def get_detail_url(obj, user):
    """Return the color for a given status."""
    return obj.get_detail_url(user)


@register.filter
def lookup(dikt, key):
    """Return a value from a dictionary or 'unknown'."""
    if dikt is None:
        return "unknown"
    return dikt.get(key, "unknown")


@register.filter
def is_project_owner(user, project):
    """Return if a user is owner of the project."""
    return project.group.owner == user


@register.filter
def is_project_delegate(user, project):
    """Return if a user is owner of the project."""
    return project.delegate == user


@register.filter
def order_by(queryset, order):
    """Return a sorted queryset."""
    return queryset.order_by(order)


@register.simple_tag
def get_posix_group_name(name):
    """Return the group name."""
    return f"{POSIX_AG_PREFIX}{name}"


@register.simple_tag
def get_posix_project_name(name):
    """Return the project name."""
    return f"{POSIX_PROJECT_PREFIX}{name}"


@register.filter
def storage_progress_color(status):
    """Return the color for the storage progress."""
    if status == HpcQuotaStatus.GREEN:
        return "success"
    if status == HpcQuotaStatus.YELLOW:
        return "warning"
    return "danger"


@register.simple_tag
def subtier_active(obj, tier):
    if obj.resources_used is None:
        return False
    return obj.resources_used.get(tier) is not None


@register.simple_tag
def tier_active(obj, subtierA, subtierB):
    return subtier_active(obj, subtierA) or subtier_active(obj, subtierB)


@register.filter
def highlight_folder(text, word):
    """Highlight a word in a text."""
    if (
        word
        in [
            "home",
            "work",
            "scratch",
            "mirrored",
            "unmirrored",
        ]
        and word in text
    ):
        return mark_safe(text.replace(word, f"<strong><u>{word}</u></strong>"))
    return text
