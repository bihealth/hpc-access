import rules

from django.urls import reverse
from test_plus.test import TestCase

from usersec.models import HpcGroupCreateRequest
from usersec.tests.factories import (
    HPCGROUPCREATEREQUESTFORM_DATA_VALID,
    HpcGroupCreateRequestFactory,
    HpcGroupFactory,
    HpcUserFactory,
)


class TestRulesBase(TestCase):
    """Test base for rules."""

    def setUp(self):
        # Init superuser
        self.superuser = self.make_user("superuser")
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        # HPC Admin
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()

        # User
        self.user = self.make_user("user")

        # Owner
        self.user_owner = self.make_user("owner")

        # Delegate
        self.user_delegate = self.make_user("delegate")

        # Member
        self.user_member = self.make_user("member")

        # User without group
        self.user_no_group = self.make_user("user_no_group")

        # Pending user
        self.user_pending = self.make_user("pending")

        self.hpc_owner = HpcUserFactory(user=self.user_owner)
        self.hpc_delegate = HpcUserFactory(user=self.user_delegate)
        self.hpc_member = HpcUserFactory(user=self.user_member)
        self.hpc_user_no_group = HpcUserFactory(user=self.user_no_group)
        self.hpc_group_request = HpcGroupCreateRequestFactory(requester=self.user_pending)

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

    def assert_permissions_granted(self, perm, group, users):
        for user in users:
            self.assertTrue(user.has_perm(perm, group), msg=f"user={user.username}")

    def assert_permissions_denied(self, perm, group, users):
        for user in users:
            self.assertFalse(user.has_perm(perm, group), msg=f"user={user.username}")

    def _send_request(self, url, method, req_kwargs):
        req_method = getattr(self.client, method.lower())

        if not req_method:
            raise ValueError(f"Invalid method '{method}'")

        return req_method(url, **req_kwargs)

    def assert_permissions_on_url(
        self,
        users,
        url,
        method,
        status_code,
        redirect_url=None,
        req_kwargs=None,
        lazy_url_callback=None,
        lazy_arg=None,
    ):
        if req_kwargs is None:
            req_kwargs = {}

        else:
            req_kwargs = {"data": req_kwargs}

        for user in users:
            with self.login(user):
                response = self._send_request(url, method, req_kwargs)
                self.assertEqual(
                    response.status_code,
                    status_code,
                    msg=f"user={user.username}",
                )

                if status_code == 302:
                    if lazy_url_callback:
                        if lazy_arg == "user":
                            redirect_url = lazy_url_callback(user)

                        else:
                            redirect_url = lazy_url_callback()

                    self.assertEqual(response.url, redirect_url, msg=f"user={user.username}")


class TestRules(TestRulesBase):

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


class TestPermissions(TestRulesBase):
    """Tests for permissions without views."""

    def test_view_hpcgroup(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
        ]
        bad_users = [self.user_hpcadmin, self.user_no_group, self.user]
        perm = "usersec.view_hpcgroup"
        self.assert_permissions_granted(perm, self.hpc_group, good_users)
        self.assert_permissions_denied(perm, self.hpc_group, bad_users)

    def test_view_hpcgroupcreaterequest(self):
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]
        perm = "usersec.view_hpcgroupcreaterequest"
        self.assert_permissions_granted(perm, self.hpc_group_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_group_request, bad_users)

    def test_create_hpcgroupcreaterequest(self):
        good_users = [self.superuser, self.user]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user_pending,
        ]
        perm = "usersec.create_hpcgroupcreaterequest"
        self.assert_permissions_granted(perm, None, good_users)
        self.assert_permissions_denied(perm, None, bad_users)

    def test_view_hpcuser(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
        ]
        bad_users = [
            self.user_hpcadmin,
            self.user_no_group,
            self.user,
        ]
        perm = "usersec.view_hpcuser"
        self.assert_permissions_granted(perm, self.hpc_member, good_users)
        self.assert_permissions_denied(perm, self.hpc_member, bad_users)


class TestPermissionsInViews(TestRulesBase):
    """Tests for permissions in views."""

    def test_home_view(self):
        url = reverse("home")
        admin_users = [self.user_hpcadmin]
        orphan_users = [self.superuser, self.user]
        hpc_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
        ]
        pending_users = [self.user_pending]

        self.assert_permissions_on_url(
            orphan_users,
            url,
            "GET",
            302,
            redirect_url=reverse("usersec:orphan-user"),
        )
        self.assert_permissions_on_url(
            hpc_users,
            url,
            "GET",
            302,
            lazy_url_callback=lambda user: reverse(
                "usersec:hpcuser-overview",
                kwargs={"hpcuser": user.hpcuser_user.first().uuid},
            ),
            lazy_arg="user",
        )
        self.assert_permissions_on_url(
            pending_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
            ),
        )
        self.assert_permissions_on_url(
            admin_users,
            url,
            "GET",
            302,
            redirect_url=reverse("adminsec:overview"),
        )

    def test_orphan_user_view_get(self):
        url = reverse("usersec:orphan-user")
        good_users = [self.superuser, self.user]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user_pending,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_orphan_user_view_post(self):
        url = reverse("usersec:orphan-user")
        good_users = [self.superuser, self.user]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user_pending,
        ]
        data = dict(HPCGROUPCREATEREQUESTFORM_DATA_VALID)

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            lazy_url_callback=lambda: reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": HpcGroupCreateRequest.objects.last().uuid},
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
            "usersec:hpcgroupcreaterequest-detail",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_update_view_get(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-update",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_update_view_post(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-update",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
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
                "usersec:hpcgroupcreaterequest-detail",
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

    def test_hpc_group_create_request_retract_view_get(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-retract",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_retract_view_post(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-retract",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_reactivate_view(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-reactivate",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_user_view(self):
        url = reverse(
            "usersec:hpcuser-overview",
            kwargs={"hpcuser": self.hpc_member.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_no_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))
