import rules
from django.urls import reverse
from test_plus.test import TestCase

from usersec.tests.factories import (
    HpcUserFactory,
    HPCGROUPCREATEREQUESTFORM_DATA_VALID,
    HpcGroupCreateRequestFactory,
    HpcGroupFactory,
)


class TestBase(TestCase):
    def setUp(self):
        # Init superuser
        self.superuser = self.make_user("superuser")
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        # User
        self.user = self.make_user("user")

        # Owner
        self.owner = self.make_user("owner")

        # Delegate
        self.delegate = self.make_user("delegate")

        # Member
        self.member = self.make_user("member")

        # User without group
        self.user_no_group = self.make_user("user_no_group")

        # Pending user
        self.pending = self.make_user("pending")

        self.hpc_owner = HpcUserFactory(user=self.owner)
        self.hpc_delegate = HpcUserFactory(user=self.delegate)
        self.hpc_member = HpcUserFactory(user=self.member)
        self.hpc_user_no_group = HpcUserFactory(user=self.user_no_group)
        self.hpc_group_request = HpcGroupCreateRequestFactory(requester=self.pending)

        self.hpc_group = HpcGroupFactory(
            owner=self.hpc_owner,
            delegate=self.hpc_delegate,
        )

        self.hpc_owner.primary_group = self.hpc_group
        self.hpc_owner.save()
        self.hpc_delegate.primary_group = self.hpc_group
        self.hpc_delegate.save()
        self.hpc_member.primary_group = self.hpc_group
        self.hpc_member.save()


class TestRules(TestBase):
    """Tests for rules."""

    def test_is_cluster_user_false(self):
        self.assertFalse(rules.test_rule("is_cluster_user", self.user))

    def test_is_cluster_user_true(self):
        HpcUserFactory(user=self.user)
        self.assertTrue(rules.test_rule("is_cluster_user", self.user))

    def test_has_pending_group_request_false(self):
        HpcUserFactory(user=self.user)
        self.assertFalse(rules.test_rule("has_pending_group_request", self.user))

    def test_has_pending_group_request_true(self):
        HpcGroupCreateRequestFactory(requester=self.user)
        self.assertTrue(rules.test_rule("has_pending_group_request", self.user))


class TestPermissions(TestBase):
    """Tests for permissions without views."""

    def assert_permissions_granted(self, perm, group, users):
        for user in users:
            self.assertTrue(user.has_perm(perm, group), msg=f"user={user.username}")

    def assert_permissions_denied(self, perm, group, users):
        for user in users:
            self.assertFalse(user.has_perm(perm, group), msg=f"user={user.username}")

    def test_view_hpcgroup(self):
        good_users = [self.owner, self.delegate, self.member]
        bad_users = [self.user_no_group, self.user]
        perm = "usersec.view_hpcgroup"
        self.assert_permissions_granted(perm, self.hpc_group, good_users)
        self.assert_permissions_denied(perm, self.hpc_group, bad_users)

    def test_view_hpcgroupcreaterequest(self):
        good_users = [self.pending]
        bad_users = [self.owner, self.delegate, self.member, self.user_no_group, self.user]
        perm = "usersec.view_hpcgroupcreaterequest"
        self.assert_permissions_granted(perm, self.hpc_group_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_group_request, bad_users)

    def test_create_hpcgroupcreaterequest(self):
        good_users = [self.user]
        bad_users = [self.owner, self.delegate, self.member, self.user_no_group, self.pending]
        perm = "usersec.create_hpcgroupcreaterequest"
        self.assert_permissions_granted(perm, None, good_users)
        self.assert_permissions_denied(perm, None, bad_users)

    def test_view_hpcuser(self):
        good_users = [self.owner, self.delegate]
        bad_users = [self.member, self.user_no_group, self.user]
        perm = "usersec.view_hpcuser"
        self.assert_permissions_granted(perm, self.hpc_group, good_users)
        self.assert_permissions_denied(perm, self.hpc_group, bad_users)


class TestPermissionsInViews(TestBase):
    """Tests for permissions in views."""

    def _send_request(self, url, method, req_kwargs):
        req_method = getattr(self.client, method.lower())

        if not req_method:
            raise ValueError(f"Invalid method '{method}'")

        return req_method(url, **req_kwargs)

    def assert_permissions_on_url(
        self, users, url, method, status_code, redirect_url=None, req_kwargs=None
    ):
        if req_kwargs is None:
            req_kwargs = {}

        for user in users:
            with self.login(user):
                response = self._send_request(url, method, req_kwargs)
                self.assertEqual(response.status_code, status_code, msg=f"user={user.username}")

                if status_code == 302:
                    self.assertEqual(response.url, redirect_url, msg=f"user={user.username}")

    def test_home_view(self):
        url = reverse("home")
        orphan_users = [self.user]
        hpc_users = [self.owner, self.delegate, self.member, self.user_no_group]
        pending_users = [self.pending]

        self.assert_permissions_on_url(
            orphan_users, url, "GET", 302, redirect_url=reverse("usersec:orphan-user")
        )
        self.assert_permissions_on_url(
            hpc_users, url, "GET", 302, redirect_url=reverse("usersec:dummy")
        )
        self.assert_permissions_on_url(
            pending_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:pending-group-request",
                kwargs={"hpcgrouprequest": self.hpc_group_request.uuid},
            ),
        )

    def test_orphan_user_view_get(self):
        url = reverse("usersec:orphan-user")
        good_users = [self.user]
        bad_users = [self.owner, self.delegate, self.member, self.user_no_group, self.pending]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_orphan_user_view_post(self):
        url = reverse("usersec:orphan-user")
        good_users = [self.user]
        bad_users = [self.owner, self.delegate, self.member, self.user_no_group, self.pending]
        data = dict(HPCGROUPCREATEREQUESTFORM_DATA_VALID)

        self.assert_permissions_on_url(good_users, url, "POST", 200, req_kwargs=data)
        self.assert_permissions_on_url(
            bad_users, url, "POST", 302, req_kwargs=data, redirect_url=reverse("home")
        )

    def test_pending_group_request_view(self):
        url = reverse(
            "usersec:pending-group-request", kwargs={"hpcgrouprequest": self.hpc_group_request.uuid}
        )
        good_users = [self.pending]
        bad_users = [self.owner, self.delegate, self.member, self.user_no_group, self.user]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))
