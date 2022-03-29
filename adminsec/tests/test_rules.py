from django.urls import reverse

from usersec.tests.factories import HPCGROUPCREATEREQUESTFORM_DATA_VALID
from usersec.tests.test_rules import TestRulesBase


class TestPermissions(TestRulesBase):

    """Tests for permissions without views."""

    def test_hpcadmin_is_not_superuser(self):
        self.assertFalse(self.user_hpcadmin.is_superuser)

    def test_superuser_is_not_hpcadmin(self):
        self.assertFalse(self.superuser.is_hpcadmin)

    def test_is_hpcadmin(self):
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]
        perm = "adminsec.is_hpcadmin"
        self.assert_permissions_granted(perm, None, good_users)
        self.assert_permissions_denied(perm, None, bad_users)


class TestPermissionsInViews(TestRulesBase):

    """Tests for permissions in views."""

    def test_admin_view(self):
        url = reverse("adminsec:overview")
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(
            bad_users, url, "GET", 302, redirect_url=reverse("home")
        )

    def test_hpc_group_create_request_approve_view(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-approve",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(
            bad_users, url, "GET", 302, redirect_url=reverse("home")
        )

    def test_hpc_group_create_request_deny_view(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-deny",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(
            bad_users, url, "GET", 302, redirect_url=reverse("home")
        )

    def test_hpc_group_create_request_revision_view_get(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-revision",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(
            bad_users, url, "GET", 302, redirect_url=reverse("home")
        )

    def test_hpc_group_create_request_revision_view_post(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-revision",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]
        data = dict(HPCGROUPCREATEREQUESTFORM_DATA_VALID)

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "adminsec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
            ),
        )
        self.assert_permissions_on_url(
            bad_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse("home"),
        )

    def test_hpc_group_create_request_detail_view(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-detail",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(
            bad_users, url, "GET", 302, redirect_url=reverse("home")
        )
