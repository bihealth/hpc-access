"""
With these settings, tests run faster.
"""

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="E3nPARlNdNctdf3E8j6Sxn5tDoD8ZpTBynM9os4c0sG7O7uY0HVfBzfKW6P3RQp2",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Your stuff...
# ------------------------------------------------------------------------------

SEND_EMAIL = True
ENABLE_LDAP = True
ENABLE_LDAP_SECONDARY = True

AUTH_LDAP_USERNAME_DOMAIN = "CHARITE"
AUTH_LDAP2_USERNAME_DOMAIN = "MDC-BERLIN"

AUTH_LDAP_DOMAIN_PRINTABLE = "Charité"
AUTH_LDAP2_DOMAIN_PRINTABLE = "MDC"

INSTITUTE_EMAIL_DOMAINS = "charite.de"
INSTITUTE2_EMAIL_DOMAINS = "mdc-berlin.de"

INSTITUTE_USERNAME_SUFFIX = "c"
INSTITUTE2_USERNAME_SUFFIX = "m"

# Snapshot Testing
# ------------------------------------------------------------------------------

TEST_RUNNER = "snapshottest.django.TestRunner"
