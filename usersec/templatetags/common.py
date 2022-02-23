from importlib import import_module

from django import template
from django.conf import settings


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
