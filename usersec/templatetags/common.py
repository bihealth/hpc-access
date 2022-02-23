from django import template
from django.conf import settings


register = template.Library()


@register.simple_tag
def get_django_setting(name, default=None):
    """
    Return value of Django setting by name or the default value if the setting
    is not found.
    """
    return getattr(settings, name, default)
