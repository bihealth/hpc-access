from importlib import import_module

from django.urls import reverse
from test_plus.test import TestCase

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
    get_detail_url,
    lookup,
    is_project_owner,
    is_project_delegate,
)
from usersec.tests.factories import HpcUserFactory, HpcGroupFactory, HpcProjectFactory

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

    def test_get_detail_url(self):
        user = self.make_user("user")
        hpcuser = HpcUserFactory(user=user)
        url = get_detail_url(hpcuser, user)
        expected = reverse("usersec:hpcuser-detail", kwargs={"hpcuser": hpcuser.uuid})
        self.assertEqual(url, expected)

    def test_lookup(self):
        data = {"key": "value"}
        self.assertEqual(lookup(data, "key"), "value")
        self.assertEqual(lookup(data, "nonsense"), "unknown")

    def test_is_project_owner(self):
        user = self.make_user("user")
        hpcuser = HpcUserFactory(user=user)
        hpcgroup = HpcGroupFactory(owner=hpcuser)
        hpcproject = HpcProjectFactory(group=hpcgroup)
        self.assertTrue(is_project_owner(hpcuser, hpcproject))
        self.assertFalse(is_project_delegate(hpcuser, hpcproject))

    def test_is_project_delegate(self):
        user = self.make_user("user")
        user2 = self.make_user("user2")
        hpcuser = HpcUserFactory(user=user)
        delegate = HpcUserFactory(user=user2)
        hpcgroup = HpcGroupFactory(owner=hpcuser)
        hpcproject = HpcProjectFactory(group=hpcgroup, delegate=delegate)
        self.assertFalse(is_project_owner(delegate, hpcproject))
        self.assertTrue(is_project_delegate(delegate, hpcproject))
