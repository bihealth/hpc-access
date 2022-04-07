from importlib import import_module
from django.test import TestCase

from django.conf import settings

from usersec.models import (
    REQUEST_STATUS_INITIAL,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_REVISION,
    REQUEST_STATUS_REVISED,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_RETRACTED,
    OBJECT_STATUS_INITIAL,
    OBJECT_STATUS_ACTIVE,
    OBJECT_STATUS_DELETED,
    OBJECT_STATUS_EXPIRED,
)
from usersec.templatetags.common import (
    get_django_setting,
    site_version,
    colorize_object_status,
    colorize_request_status,
)

site = import_module(settings.SITE_PACKAGE)


class TestCommon(TestCase):

    """Tests for templatetags/common.py"""

    def test_get_django_setting(self):
        self.assertEqual(get_django_setting("SITE_ID"), settings.SITE_ID)

    def test_site_version(self):
        self.assertEqual(site_version(), site.__version__)

    def test_colorize_request_status(self):
        data = {
            REQUEST_STATUS_INITIAL: "info",
            REQUEST_STATUS_ACTIVE: "info",
            REQUEST_STATUS_REVISION: "warning",
            REQUEST_STATUS_REVISED: "info",
            REQUEST_STATUS_APPROVED: "success",
            REQUEST_STATUS_DENIED: "danger",
            REQUEST_STATUS_RETRACTED: "danger",
            "UNKNOWN": "dark",
        }

        for key, expected in data.items():
            self.assertEqual(colorize_request_status(key), expected)

    def test_colorize_object_status(self):
        data = {
            OBJECT_STATUS_INITIAL: "info",
            OBJECT_STATUS_ACTIVE: "success",
            OBJECT_STATUS_DELETED: "muted",
            OBJECT_STATUS_EXPIRED: "warning",
            "UNKNOWN": "dark",
        }

        for key, expected in data.items():
            self.assertEqual(colorize_object_status(key), expected)
