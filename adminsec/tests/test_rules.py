from unittest.mock import patch

from django.conf import settings
from django.urls import reverse

from usersec.models import (
    HpcUserCreateRequest,
    HpcGroupCreateRequest,
    REQUEST_STATUS_ACTIVE,
    HpcUser,
    HpcGroup,
    HpcProjectCreateRequest,
    HpcProject,
)
from usersec.tests.factories import (
    HPCGROUPCREATEREQUEST_FORM_DATA_VALID,
    HPCUSERCREATEREQUEST_FORM_DATA_VALID,
    HPCPROJECTCREATEREQUEST_FORM_DATA_VALID,
)
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
            self.user_member_other_group,
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
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_user_detail_view(self):
        url = reverse(
            "adminsec:hpcuser-detail",
            kwargs={"hpcuser": self.hpc_member.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_project_detail_view(self):
        url = reverse(
            "adminsec:hpcproject-detail",
            kwargs={"hpcproject": self.hpc_project.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_detail_view(self):
        url = reverse(
            "adminsec:hpcgroup-detail",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_approve_view_get(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-approve",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_approve_view_post(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-approve",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        def rollback_callback():
            u = HpcGroupCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()
            HpcUser.objects.last().delete()
            HpcGroup.objects.last().delete()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "adminsec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
            ),
            rollback_callback=rollback_callback,
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_deny_view_get(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-deny",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_deny_view_post(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-deny",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        data = {"comment": "Request denied!"}
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        def rollback_callback():
            u = HpcGroupCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "adminsec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
            ),
            req_kwargs=data,
            rollback_callback=rollback_callback,
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_revision_view_get(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-revision",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_create_request_revision_view_post(self):
        url = reverse(
            "adminsec:hpcgroupcreaterequest-revision",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCGROUPCREATEREQUEST_FORM_DATA_VALID)

        def rollback_callback():
            u = HpcGroupCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "adminsec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
            ),
            rollback_callback=rollback_callback,
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
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_user_create_request_approve_view_get(self):
        url = reverse(
            "adminsec:hpcusercreaterequest-approve",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @patch("adminsec.ldap.LdapConnector.connect")
    @patch("adminsec.ldap.LdapConnector.get_ldap_username_domain_by_mail")
    def test_hpc_user_create_request_approve_view_post(
        self, mock_get_ldap_username_domain_by_mail, mock_connect
    ):
        mock_get_ldap_username_domain_by_mail.return_value = (
            "new_user",
            settings.AUTH_LDAP_USERNAME_DOMAIN,
        )
        url = reverse(
            "adminsec:hpcusercreaterequest-approve",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        def rollback_callback():
            u = HpcUserCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()
            HpcUser.objects.filter(
                username="new_user_" + settings.INSTITUTE_USERNAME_SUFFIX
            ).delete()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "adminsec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
            ),
            rollback_callback=rollback_callback,
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    def test_hpc_user_create_request_deny_view_get(self):
        url = reverse(
            "adminsec:hpcusercreaterequest-deny",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_user_create_request_deny_view_post(self):
        url = reverse(
            "adminsec:hpcusercreaterequest-deny",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        data = {"comment": "Request denied!"}
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        def rollback_callback():
            u = HpcUserCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "adminsec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
            ),
            req_kwargs=data,
            rollback_callback=rollback_callback,
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    def test_hpc_user_create_request_revision_view_get(self):
        url = reverse(
            "adminsec:hpcusercreaterequest-revision",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_user_create_request_revision_view_post(self):
        url = reverse(
            "adminsec:hpcusercreaterequest-revision",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCUSERCREATEREQUEST_FORM_DATA_VALID)

        def rollback_callback():
            u = HpcUserCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "adminsec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
            ),
            rollback_callback=rollback_callback,
        )
        self.assert_permissions_on_url(
            bad_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse("home"),
        )

    def test_hpc_user_create_request_detail_view(self):
        url = reverse(
            "adminsec:hpcusercreaterequest-detail",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_project_create_request_approve_view_get(self):
        url = reverse(
            "adminsec:hpcprojectcreaterequest-approve",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_project_create_request_approve_view_post(self):
        url = reverse(
            "adminsec:hpcprojectcreaterequest-approve",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        def rollback_callback():
            u = HpcProjectCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()
            HpcProject.objects.filter(name=self.hpc_project_create_request.name).delete()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "adminsec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
            ),
            rollback_callback=rollback_callback,
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    def test_hpc_project_create_request_deny_view_get(self):
        url = reverse(
            "adminsec:hpcprojectcreaterequest-deny",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_project_create_request_deny_view_post(self):
        url = reverse(
            "adminsec:hpcprojectcreaterequest-deny",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        data = {"comment": "Request denied!"}
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        def rollback_callback():
            u = HpcProjectCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "adminsec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
            ),
            req_kwargs=data,
            rollback_callback=rollback_callback,
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    def test_hpc_project_create_request_revision_view_get(self):
        url = reverse(
            "adminsec:hpcprojectcreaterequest-revision",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_project_create_request_revision_view_post(self):
        url = reverse(
            "adminsec:hpcprojectcreaterequest-revision",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCPROJECTCREATEREQUEST_FORM_DATA_VALID)
        data["members"] = [m.id for m in self.hpc_project_create_request.members.all()]

        def rollback_callback():
            u = HpcProjectCreateRequest.objects.last()
            u.status = REQUEST_STATUS_ACTIVE
            u.save()

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "adminsec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
            ),
            rollback_callback=rollback_callback,
        )
        self.assert_permissions_on_url(
            bad_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse("home"),
        )

    def test_hpc_project_create_request_detail_view(self):
        url = reverse(
            "adminsec:hpcprojectcreaterequest-detail",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [self.superuser, self.user_hpcadmin]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))
