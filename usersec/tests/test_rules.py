import rules
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from test_plus.test import TestCase

from usersec.models import (
    HpcGroupCreateRequest,
    HpcProjectChangeRequest,
    HpcProjectCreateRequest,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
)
from usersec.tests.factories import (
    HPCGROUPCHANGEREQUEST_FORM_DATA_VALID,
    HPCGROUPCREATEREQUEST_FORM_DATA_VALID,
    HPCPROJECTCHANGEREQUEST_FORM_DATA_VALID,
    HPCPROJECTCREATEREQUEST_FORM_DATA_VALID,
    HPCUSERCHANGEREQUEST_FORM_DATA_VALID,
    HPCUSERCREATEREQUEST_FORM_DATA_VALID,
    HpcGroupChangeRequestFactory,
    HpcGroupCreateRequestFactory,
    HpcGroupFactory,
    HpcGroupInvitationFactory,
    HpcProjectChangeRequestFactory,
    HpcProjectCreateRequestFactory,
    HpcProjectFactory,
    HpcProjectInvitationFactory,
    HpcUserChangeRequestFactory,
    HpcUserCreateRequestFactory,
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
        self.user.consented_to_terms = True
        self.user.save()

        # Owner
        self.user_owner = self.make_user("owner")
        self.user_owner.name = "Group Owner"
        self.user_owner.consented_to_terms = True
        self.user_owner.save()

        # Delegate
        self.user_delegate = self.make_user("delegate")
        self.user_delegate.consented_to_terms = True
        self.user_delegate.save()

        # Member
        self.user_member = self.make_user("member")
        self.user_member.consented_to_terms = True
        self.user_member.save()

        # User for user-centric views
        self.user_member2 = self.make_user("member2")
        self.user_member2.consented_to_terms = True
        self.user_member2.save()

        # User without group
        self.user_member_other_group = self.make_user("member_no_group")
        self.user_member_other_group.consented_to_terms = True
        self.user_member_other_group.save()

        # Pending user
        self.user_pending = self.make_user("pending@" + settings.AUTH_LDAP_USERNAME_DOMAIN)
        self.user_pending.name = "John Doe"
        self.user_pending.consented_to_terms = True
        self.user_pending.save()

        # Invited user
        self.user_invited = self.make_user("invited@" + settings.AUTH_LDAP_USERNAME_DOMAIN)

        # Create HPC groups
        self.hpc_group = HpcGroupFactory()
        self.hpc_other_group = HpcGroupFactory()

        # Create HPC project
        self.hpc_project = HpcProjectFactory(group=self.hpc_group)

        # Create HPC users
        self.hpc_owner = HpcUserFactory(user=self.user_owner, primary_group=self.hpc_group)
        self.hpc_delegate = HpcUserFactory(user=self.user_delegate, primary_group=self.hpc_group)
        self.hpc_member = HpcUserFactory(user=self.user_member, primary_group=self.hpc_group)
        self.hpc_member2 = HpcUserFactory(user=self.user_member2, primary_group=self.hpc_group)
        self.hpc_member_other_group = HpcUserFactory(
            user=self.user_member_other_group,
            primary_group=self.hpc_other_group,
        )

        # Set group owner and delegate
        self.hpc_group.owner = self.hpc_owner
        self.hpc_group.delegate = self.hpc_delegate
        self.hpc_group.save()

        # Set project group, delegate and members
        self.hpc_project.delegate = self.hpc_member_other_group
        self.hpc_project.members.add(self.hpc_owner, self.hpc_member, self.hpc_member_other_group)
        self.hpc_project.save()

        # Create HPC group create request
        self.hpc_group_create_request = HpcGroupCreateRequestFactory(requester=self.user_pending)

        # Create HPC group change request
        self.hpc_group_change_request = HpcGroupChangeRequestFactory(
            requester=self.user_owner, group=self.hpc_group
        )

        # Create HPC user create request
        self.hpc_user_create_request = HpcUserCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group
        )

        # Create HPC user change request
        self.hpc_user_change_request = HpcUserChangeRequestFactory(
            requester=self.user_owner, user=self.hpc_member
        )

        # Create HPC project create request
        self.hpc_project_create_request = HpcProjectCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group
        )
        self.hpc_project_create_request.members.add(
            self.hpc_owner, self.hpc_member, self.hpc_member_other_group
        )

        # Create HPC project change request
        self.hpc_project_change_request = HpcProjectChangeRequestFactory(
            requester=self.user_owner, project=self.hpc_project
        )
        self.hpc_project_change_request.members.add(
            self.hpc_owner, self.hpc_member, self.hpc_member_other_group
        )

        # Create HPC project invitation
        self.hpc_project_invitation = HpcProjectInvitationFactory(
            user=self.hpc_member2,
            project=self.hpc_project,
            hpcprojectcreaterequest=self.hpc_project_create_request,
        )

        # Create HPC group invitation
        self.hpc_group_invitation = HpcGroupInvitationFactory(
            hpcusercreaterequest=self.hpc_user_create_request, username=self.user_invited.username
        )
        self.hpc_group_invitation.hpcusercreaterequest.group = self.hpc_group
        self.hpc_group_invitation.hpcusercreaterequest.save()

    def assert_permissions_granted(self, perm, obj, users):
        for user in users:
            self.assertTrue(user.has_perm(perm, obj), msg=f"user={user.username}")

    def assert_permissions_denied(self, perm, obj, users):
        for user in users:
            self.assertFalse(user.has_perm(perm, obj), msg=f"user={user.username}")

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
        rollback_callback=None,
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

            if rollback_callback:
                rollback_callback()


class TestRules(TestRulesBase):
    """Tests for rules."""

    def test_is_cluster_user_false(self):
        self.assertFalse(rules.test_rule("usersec.is_cluster_user", self.user_pending))

    def test_is_cluster_user_true(self):
        self.assertTrue(rules.test_rule("usersec.is_cluster_user", self.user_member))

    def test_has_pending_group_request_false(self):
        self.assertFalse(rules.test_rule("usersec.has_pending_group_request", self.user))

    def test_has_pending_group_request_true(self):
        self.assertTrue(rules.test_rule("usersec.has_pending_group_request", self.user_pending))

    def test_is_group_manager_owner_true(self):
        self.assertTrue(
            rules.test_rule("usersec.is_group_manager", self.user_owner, self.hpc_group)
        )

    def test_is_group_manager_delegate_true(self):
        self.assertTrue(
            rules.test_rule("usersec.is_group_manager", self.user_delegate, self.hpc_group)
        )

    def test_is_group_manager_member_false(self):
        self.assertFalse(
            rules.test_rule("usersec.is_group_manager", self.user_member, self.hpc_group)
        )

    def test_is_project_manager_owner_true(self):
        self.assertTrue(
            rules.test_rule("usersec.is_project_manager", self.user_owner, self.hpc_project)
        )

    def test_is_project_manager_delegate_true(self):
        self.assertTrue(
            rules.test_rule(
                "usersec.is_project_manager", self.user_member_other_group, self.hpc_project
            )
        )

    def test_is_project_manager_group_delegate_true(self):
        self.assertTrue(
            rules.test_rule("usersec.is_project_manager", self.user_delegate, self.hpc_project)
        )

    def test_is_project_manager_member_false(self):
        self.assertFalse(
            rules.test_rule("usersec.is_project_manager", self.user_member, self.hpc_project)
        )

    def test_has_group_invitation_true(self):
        self.assertTrue(rules.test_rule("usersec.has_group_invitation", self.user_invited))

    def test_has_group_invitation_false(self):
        self.assertFalse(rules.test_rule("usersec.has_group_invitation", self.user))


class TestPermissions(TestRulesBase):
    """Tests for permissions without views."""

    def _test_view_mode_denied(self, perm, obj):
        users = [
            self.user_owner,
            self.user_delegate,
        ]
        self.assert_permissions_denied(perm, obj, users)

    def _test_view_mode_granted(self, perm, obj):
        users = [
            self.user_owner,
            self.user_delegate,
        ]
        self.assert_permissions_granted(perm, obj, users)

    def test_view_hpcuser(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
        ]
        bad_users = [
            self.user_hpcadmin,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.view_hpcuser"
        self.assert_permissions_granted(perm, self.hpc_member, good_users)
        self.assert_permissions_denied(perm, self.hpc_member, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcuser_view_mode(self):
        self._test_view_mode_granted("usersec.view_hpcuser", self.hpc_member)

    def test_view_hpcusercreaterequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.view_hpcusercreaterequest"
        self.assert_permissions_granted(perm, self.hpc_user_create_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_user_create_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcusercreaterequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.view_hpcusercreaterequest", self.hpc_user_create_request
        )

    def test_create_hpcusercreaterequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.create_hpcusercreaterequest"
        self.assert_permissions_granted(perm, self.hpc_group, good_users)
        self.assert_permissions_denied(perm, self.hpc_group, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_create_hpcusercreaterequest_view_mode(self):
        self._test_view_mode_denied("usersec.create_hpcusercreaterequest", self.hpc_group)

    def test_manage_hpcusercreaterequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.manage_hpcusercreaterequest"
        self.assert_permissions_granted(perm, self.hpc_user_create_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_user_create_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_manage_hpcusercreaterequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.manage_hpcusercreaterequest", self.hpc_user_create_request
        )

    def test_view_hpcuserchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.view_hpcuserchangerequest"
        self.assert_permissions_granted(perm, self.hpc_user_change_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_user_change_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcuserchangerequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.view_hpcuserchangerequest", self.hpc_user_change_request
        )

    def test_create_hpcuserchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.create_hpcuserchangerequest"
        self.assert_permissions_granted(perm, self.hpc_member, good_users)
        self.assert_permissions_denied(perm, self.hpc_member, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_create_hpcuserchangerequest_view_mode(self):
        self._test_view_mode_denied("usersec.create_hpcuserchangerequest", self.hpc_member)

    def test_manage_hpcuserchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.manage_hpcuserchangerequest"
        self.assert_permissions_granted(perm, self.hpc_user_change_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_user_change_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_manage_hpcuserchangerequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.manage_hpcuserchangerequest", self.hpc_user_change_request
        )

    def test_view_hpcproject(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_hpcadmin,
            self.user_member2,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.view_hpcproject"
        self.assert_permissions_granted(perm, self.hpc_project, good_users)
        self.assert_permissions_denied(perm, self.hpc_project, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcproject_view_mode(self):
        self._test_view_mode_granted("usersec.view_hpcproject", self.hpc_project)

    def test_view_hpcprojectcreaterequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.view_hpcprojectcreaterequest"
        self.assert_permissions_granted(perm, self.hpc_project_create_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_project_create_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcprojectcreaterequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.view_hpcprojectcreaterequest", self.hpc_project_create_request
        )

    def test_create_hpcprojectcreaterequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.create_hpcprojectcreaterequest"
        self.assert_permissions_granted(perm, self.hpc_group, good_users)
        self.assert_permissions_denied(perm, self.hpc_group, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_create_hpcprojectcreaterequest_view_mode(self):
        self._test_view_mode_denied("usersec.create_hpcprojectcreaterequest", self.hpc_group)

    def test_manage_hpcprojectcreaterequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.manage_hpcprojectcreaterequest"
        self.assert_permissions_granted(perm, self.hpc_project_create_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_project_create_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_manage_hpcprojectcreaterequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.manage_hpcprojectcreaterequest", self.hpc_project_create_request
        )

    def test_view_hpcprojectchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.view_hpcprojectchangerequest"
        self.assert_permissions_granted(perm, self.hpc_project_change_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_project_change_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcprojectchangerequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.view_hpcprojectchangerequest", self.hpc_project_change_request
        )

    def test_create_hpcprojectchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.create_hpcprojectchangerequest"
        self.assert_permissions_granted(perm, self.hpc_project, good_users)
        self.assert_permissions_denied(perm, self.hpc_project, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_create_hpcprojectchangerequest_view_mode(self):
        self._test_view_mode_denied("usersec.create_hpcprojectchangerequest", self.hpc_project)

    def test_manage_hpcprojectchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.manage_hpcprojectchangerequest"
        self.assert_permissions_granted(perm, self.hpc_project_change_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_project_change_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_manage_hpcprojectchangerequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.manage_hpcprojectchangerequest", self.hpc_project_change_request
        )

    def test_view_hpcgroup(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
        ]
        bad_users = [self.user_hpcadmin, self.user_member_other_group, self.user, self.user_invited]
        perm = "usersec.view_hpcgroup"
        self.assert_permissions_granted(perm, self.hpc_group, good_users)
        self.assert_permissions_denied(perm, self.hpc_group, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcgroup_view_mode(self):
        self._test_view_mode_granted("usersec.view_hpcgroup", self.hpc_group)

    def test_view_hpcgroupcreaterequest(self):
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.view_hpcgroupcreaterequest"
        self.assert_permissions_granted(perm, self.hpc_group_create_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_group_create_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcgroupcreaterequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.view_hpcgroupcreaterequest", self.hpc_group_create_request
        )

    def test_create_hpcgroupcreaterequest(self):
        good_users = [self.superuser, self.user]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user_pending,
            self.user_invited,
        ]
        perm = "usersec.create_hpcgroupcreaterequest"
        self.assert_permissions_granted(perm, None, good_users)
        self.assert_permissions_denied(perm, None, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_create_hpcgroupcreaterequest_view_mode(self):
        self._test_view_mode_denied("usersec.create_hpcgroupcreaterequest", None)

    def test_manage_hpcgroupcreaterequest(self):
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.manage_hpcgroupcreaterequest"
        self.assert_permissions_granted(perm, self.hpc_group_create_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_group_create_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_manage_hpcgroupcreaterequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.manage_hpcgroupcreaterequest", self.hpc_group_create_request
        )

    def test_view_hpcgroupchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.view_hpcgroupchangerequest"
        self.assert_permissions_granted(perm, self.hpc_group_change_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_group_change_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_view_hpcgroupchangerequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.view_hpcgroupchangerequest", self.hpc_group_change_request
        )

    def test_create_hpcgroupchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.create_hpcgroupchangerequest"
        self.assert_permissions_granted(perm, self.hpc_group, good_users)
        self.assert_permissions_denied(perm, self.hpc_group, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_create_hpcgroupchangerequest_view_mode(self):
        self._test_view_mode_denied("usersec.create_hpcgroupchangerequest", self.hpc_group)

    def test_manage_hpcgroupchangerequest(self):
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
            self.user_invited,
        ]
        perm = "usersec.manage_hpcgroupchangerequest"
        self.assert_permissions_granted(perm, self.hpc_group_change_request, good_users)
        self.assert_permissions_denied(perm, self.hpc_group_change_request, bad_users)

    @override_settings(VIEW_MODE=True)
    def test_manage_hpcgroupchangerequest_view_mode(self):
        self._test_view_mode_denied(
            "usersec.manage_hpcgroupchangerequest", self.hpc_group_change_request
        )

    def test_manage_hpcgroupinvitation(self):
        good_users = [self.superuser, self.user_invited]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]
        perm = "usersec.manage_hpcgroupinvitation"
        self.assert_permissions_granted(perm, self.hpc_group_invitation, good_users)
        self.assert_permissions_denied(perm, self.hpc_group_invitation, bad_users)

    def test_manage_hpcprojectinvitation(self):
        good_users = [self.superuser, self.user_member2]
        bad_users = [
            self.user_pending,
            self.user_invited,
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
            self.user,
        ]
        perm = "usersec.manage_hpcprojectinvitation"
        self.assert_permissions_granted(perm, self.hpc_project_invitation, good_users)
        self.assert_permissions_denied(perm, self.hpc_project_invitation, bad_users)


class TestPermissionsInViews(TestRulesBase):
    """Tests for permissions in views."""

    def _test_view_mode_denied(self, url, method="GET"):
        users = [
            self.user_owner,
            self.user_delegate,
        ]
        self.assert_permissions_on_url(
            users,
            url,
            method,
            302,
            redirect_url=reverse("home"),
        )

    def _test_view_mode_granted(self, url, method="GET"):
        users = [
            self.user_owner,
            self.user_delegate,
        ]
        self.assert_permissions_on_url(
            users,
            url,
            method,
            200,
        )

    def test_home_view(self):
        url = reverse("home")
        admin_users = [self.user_hpcadmin]
        superusers = [self.superuser]
        orphan_users = [self.user]
        hpc_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
        ]
        pending_users = [self.user_pending]

        self.assert_permissions_on_url(
            superusers,
            url,
            "GET",
            302,
            redirect_url=reverse("admin-landing"),
        )
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
            200,
        )
        self.assert_permissions_on_url(
            pending_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
            ),
        )
        self.assert_permissions_on_url(
            admin_users,
            url,
            "GET",
            302,
            redirect_url=reverse("adminsec:overview"),
        )

    @override_settings(VIEW_MODE=True)
    def test_home_view_view_mode(self):
        url = reverse("home")
        admin_users = [self.user_hpcadmin]
        superusers = [self.superuser]
        orphan_users = [self.user]
        hpc_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
        ]
        pending_users = [self.user_pending]

        self.assert_permissions_on_url(
            superusers,
            url,
            "GET",
            302,
            redirect_url=reverse("admin-landing"),
        )
        self.assert_permissions_on_url(
            orphan_users,
            url,
            "GET",
            302,
            redirect_url=reverse("usersec:view-mode-enabled"),
        )
        self.assert_permissions_on_url(
            hpc_users,
            url,
            "GET",
            200,
        )
        self.assert_permissions_on_url(
            pending_users,
            url,
            "GET",
            302,
            redirect_url=reverse("usersec:view-mode-enabled"),
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
            self.user_member2,
            self.user_member_other_group,
            self.user_pending,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_orphan_user_view_get_view_mode(self):
        url = reverse("usersec:orphan-user")
        self._test_view_mode_denied(url)

    def test_orphan_user_view_post(self):
        url = reverse("usersec:orphan-user")
        good_users = [self.superuser, self.user]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user_pending,
        ]
        data = dict(HPCGROUPCREATEREQUEST_FORM_DATA_VALID)

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

    @override_settings(VIEW_MODE=True)
    def test_orphan_user_view_post_view_mode(self):
        url = reverse("usersec:orphan-user")
        self._test_view_mode_denied(url, "POST")

    def test_hpc_group_create_request_detail_view(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-detail",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_create_request_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-detail",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_create_request_update_view_get(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-update",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_create_request_update_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-update",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_create_request_update_view_post(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-update",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCGROUPCREATEREQUEST_FORM_DATA_VALID)

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_create_request_update_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-update",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_group_create_request_retract_view_get(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-retract",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_create_request_retract_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-retract",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_create_request_retract_view_post(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-retract",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_create_request_retract_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-retract",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_group_create_request_reactivate_view(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-reactivate",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        good_users = [self.superuser, self.user_pending]
        bad_users = [
            self.user_hpcadmin,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_create_request_reactivate_view_view_mode(self):
        url = reverse(
            "usersec:hpcgroupcreaterequest-reactivate",
            kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_change_request_create_view(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_change_request_create_view_view_mode(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_change_request_detail_view(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-detail",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_change_request_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-detail",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_change_request_update_view_get(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-update",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_change_request_update_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-update",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_change_request_update_view_post(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-update",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        good_users = [
            self.user_owner,
            self.user_delegate,
            self.superuser,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCGROUPCHANGEREQUEST_FORM_DATA_VALID)

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "usersec:hpcgroupchangerequest-detail",
                kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_change_request_update_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-update",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_group_change_request_retract_view_get(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-retract",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        good_users = [
            self.user_owner,
            self.user_delegate,
            self.superuser,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_change_request_retract_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-retract",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_change_request_retract_view_post(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-retract",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        good_users = [
            self.user_owner,
            self.user_delegate,
            self.superuser,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupchangerequest-detail",
                kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_change_request_retract_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-retract",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_group_change_request_reactivate_view(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-reactivate",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        good_users = [
            self.user_owner,
            self.user_delegate,
            self.superuser,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupchangerequest-detail",
                kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_change_request_reactivate_view_view_mode(self):
        url = reverse(
            "usersec:hpcgroupchangerequest-reactivate",
            kwargs={"hpcgroupchangerequest": self.hpc_group_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_view(self):
        url = reverse("usersec:hpcuser-overview")
        good_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_member_other_group,
        ]
        admin_user = [self.superuser]
        hpcadmin_user = [self.user_hpcadmin]
        orphan_user = [self.user_pending]
        bad_users = [self.user]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(
            admin_user, url, "GET", 302, redirect_url=reverse("admin-landing")
        )
        self.assert_permissions_on_url(
            hpcadmin_user, url, "GET", 302, redirect_url=reverse("adminsec:overview")
        )
        self.assert_permissions_on_url(
            orphan_user,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": self.hpc_group_create_request.uuid},
            ),
        )
        self.assert_permissions_on_url(
            bad_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:orphan-user",
            ),
        )

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_view_view_mode(self):
        url = reverse(
            "usersec:hpcuser-overview",
        )
        self._test_view_mode_granted(url)

    def test_hpc_user_detail_view(self):
        url = reverse(
            "usersec:hpcuser-detail",
            kwargs={"hpcuser": self.hpc_member.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
        ]
        bad_users = [
            self.user_hpcadmin,
            self.user_pending,
            self.user_member2,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcuser-detail",
            kwargs={"hpcuser": self.hpc_member.uuid},
        )
        self._test_view_mode_granted(url)

    def test_hpc_group_detail_view(self):
        url = reverse(
            "usersec:hpcgroup-detail",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcgroup-detail",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        self._test_view_mode_granted(url)

    def test_hpc_project_detail_view(self):
        url = reverse(
            "usersec:hpcproject-detail",
            kwargs={"hpcproject": self.hpc_project.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_pending,
            self.user_hpcadmin,
            self.user_member2,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcproject-detail",
            kwargs={"hpcproject": self.hpc_project.uuid},
        )
        self._test_view_mode_granted(url)

    def test_hpc_user_create_request_create_view_get(self):
        url = reverse(
            "usersec:hpcusercreaterequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_create_request_create_view_mode(self):
        url = reverse(
            "usersec:hpcusercreaterequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_create_request_create_view_post(self):
        url = reverse(
            "usersec:hpcusercreaterequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCUSERCREATEREQUEST_FORM_DATA_VALID)

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            lazy_url_callback=lambda: reverse(
                "usersec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": HpcUserCreateRequest.objects.last().uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_create_request_create_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcusercreaterequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_user_create_request_detail_view(self):
        url = reverse(
            "usersec:hpcusercreaterequest-detail",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_create_request_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcusercreaterequest-detail",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_create_request_update_view_get(self):
        url = reverse(
            "usersec:hpcusercreaterequest-update",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_create_request_update_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcusercreaterequest-update",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_create_request_update_view_post(self):
        url = reverse(
            "usersec:hpcusercreaterequest-update",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCUSERCREATEREQUEST_FORM_DATA_VALID)

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "usersec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_create_request_update_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcusercreaterequest-update",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_user_create_request_retract_view_get(self):
        url = reverse(
            "usersec:hpcusercreaterequest-retract",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_create_request_retract_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcusercreaterequest-retract",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_create_request_retract_view_post(self):
        url = reverse(
            "usersec:hpcusercreaterequest-retract",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_create_request_retract_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcusercreaterequest-retract",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_user_create_request_reactivate_view(self):
        url = reverse(
            "usersec:hpcusercreaterequest-reactivate",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_create_request_reactivate_view_view_mode(self):
        url = reverse(
            "usersec:hpcusercreaterequest-reactivate",
            kwargs={"hpcusercreaterequest": self.hpc_user_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_change_request_create_view_get(self):
        url = reverse(
            "usersec:hpcuserchangerequest-create",
            kwargs={"hpcuser": self.hpc_member.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_change_request_create_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcuserchangerequest-create",
            kwargs={"hpcuser": self.hpc_member.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_change_request_create_view_post(self):
        url = reverse(
            "usersec:hpcuserchangerequest-create",
            kwargs={"hpcuser": self.hpc_member.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCUSERCHANGEREQUEST_FORM_DATA_VALID)

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            lazy_url_callback=lambda: reverse(
                "usersec:hpcuserchangerequest-detail",
                kwargs={"hpcuserchangerequest": HpcUserChangeRequest.objects.last().uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_change_request_create_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcuserchangerequest-create",
            kwargs={"hpcuser": self.hpc_member.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_user_change_request_detail_view(self):
        url = reverse(
            "usersec:hpcuserchangerequest-detail",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_change_request_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcuserchangerequest-detail",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_change_request_update_view_get(self):
        url = reverse(
            "usersec:hpcuserchangerequest-update",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_change_request_update_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcuserchangerequest-update",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_change_request_update_view_post(self):
        url = reverse(
            "usersec:hpcuserchangerequest-update",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCUSERCHANGEREQUEST_FORM_DATA_VALID)

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "usersec:hpcuserchangerequest-detail",
                kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_change_request_update_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcuserchangerequest-update",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_user_change_request_retract_view_get(self):
        url = reverse(
            "usersec:hpcuserchangerequest-retract",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_change_request_retract_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcuserchangerequest-retract",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_user_change_request_retract_view_post(self):
        url = reverse(
            "usersec:hpcuserchangerequest-retract",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcuserchangerequest-detail",
                kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_change_request_retract_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcuserchangerequest-retract",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_user_change_request_reactivate_view(self):
        url = reverse(
            "usersec:hpcuserchangerequest-reactivate",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcuserchangerequest-detail",
                kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_user_change_request_reactivate_view_view_mode(self):
        url = reverse(
            "usersec:hpcuserchangerequest-reactivate",
            kwargs={"hpcuserchangerequest": self.hpc_user_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_create_request_create_view_get(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_create_request_create_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_create_request_create_view_post(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCPROJECTCREATEREQUEST_FORM_DATA_VALID)
        data["members"] = [self.hpc_owner.id]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            lazy_url_callback=lambda: reverse(
                "usersec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": HpcProjectCreateRequest.objects.last().uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_create_request_create_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-create",
            kwargs={"hpcgroup": self.hpc_group.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_project_create_request_detail_view(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-detail",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_create_request_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-detail",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_create_request_update_view_get(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-update",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_create_request_update_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-update",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_create_request_update_view_post(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-update",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]
        data = dict(HPCPROJECTCREATEREQUEST_FORM_DATA_VALID)
        data["members"] = [self.hpc_owner.id]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "usersec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_create_request_update_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-update",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_project_create_request_retract_view_get(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-retract",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_create_request_retract_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-retract",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_create_request_retract_view_post(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-retract",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_create_request_retract_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-retract",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_project_create_request_reactivate_view(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-reactivate",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_create_request_reactivate_view_view_mode(self):
        url = reverse(
            "usersec:hpcprojectcreaterequest-reactivate",
            kwargs={"hpcprojectcreaterequest": self.hpc_project_create_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_change_request_create_view_get(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-create",
            kwargs={"hpcproject": self.hpc_project.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_change_request_create_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-create",
            kwargs={"hpcproject": self.hpc_project.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_change_request_create_view_post(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-create",
            kwargs={"hpcproject": self.hpc_project.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user,
        ]
        data = dict(HPCPROJECTCHANGEREQUEST_FORM_DATA_VALID)
        data["members"] = [self.hpc_owner.id]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            lazy_url_callback=lambda: reverse(
                "usersec:hpcprojectchangerequest-detail",
                kwargs={"hpcprojectchangerequest": HpcProjectChangeRequest.objects.last().uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_change_request_create_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-create",
            kwargs={"hpcproject": self.hpc_project.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_project_change_request_detail_view(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-detail",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_change_request_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-detail",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_change_request_update_view_get(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-update",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_change_request_update_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-update",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_changee_request_update_view_post(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-update",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user,
        ]
        data = dict(HPCPROJECTCHANGEREQUEST_FORM_DATA_VALID)
        data["members"] = [self.hpc_owner.id]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            req_kwargs=data,
            redirect_url=reverse(
                "usersec:hpcprojectchangerequest-detail",
                kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
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

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_change_request_update_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-update",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_project_change_request_retract_view_get(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-retract",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_change_request_retract_view_get_view_mode(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-retract",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_project_change_request_retract_view_post(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-retract",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcprojectchangerequest-detail",
                kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_change_request_retract_view_post_view_mode(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-retract",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        self._test_view_mode_denied(url, "POST")

    def test_hpc_project_change_request_reactivate_view(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-reactivate",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner,
            self.user_delegate,
            self.user_member_other_group,
        ]
        bad_users = [
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcprojectchangerequest-detail",
                kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_project_change_request_reactivate_view_view_mode(self):
        url = reverse(
            "usersec:hpcprojectchangerequest-reactivate",
            kwargs={"hpcprojectchangerequest": self.hpc_project_change_request.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_invitation_detail_view(self):
        url = reverse(
            "usersec:hpcgroupinvitation-detail",
            kwargs={"hpcgroupinvitation": self.hpc_group_invitation.uuid},
        )
        good_users = [
            self.superuser,
            self.user_invited,
        ]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    @override_settings(VIEW_MODE=True)
    def test_hpc_group_invitation_detail_view_view_mode(self):
        url = reverse(
            "usersec:hpcgroupinvitation-detail",
            kwargs={"hpcgroupinvitation": self.hpc_group_invitation.uuid},
        )
        self._test_view_mode_denied(url)

    def test_hpc_group_invitation_accept_view(self):
        url = reverse(
            "usersec:hpcgroupinvitation-accept",
            kwargs={"hpcgroupinvitation": self.hpc_group_invitation.uuid},
        )
        good_users = [
            self.user_invited,
        ]
        not_so_good_users = [
            self.superuser,
        ]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            lazy_url_callback=lambda: reverse(
                "usersec:hpcuser-overview",
            ),
        )
        self.assert_permissions_on_url(
            not_so_good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupinvitation-detail",
                kwargs={"hpcgroupinvitation": self.hpc_group_invitation.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_invitation_reject_view_get(self):
        url = reverse(
            "usersec:hpcgroupinvitation-reject",
            kwargs={"hpcgroupinvitation": self.hpc_group_invitation.uuid},
        )
        good_users = [
            self.superuser,
            self.user_invited,
        ]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_group_invitation_reject_view_post(self):
        url = reverse(
            "usersec:hpcgroupinvitation-reject",
            kwargs={"hpcgroupinvitation": self.hpc_group_invitation.uuid},
        )
        good_users = [
            self.superuser,
            self.user_invited,
        ]
        bad_users = [
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_member2,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcgroupinvitation-detail",
                kwargs={"hpcgroupinvitation": self.hpc_group_invitation.uuid},
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))

    def test_hpc_project_invitation_accept_view(self):
        url = reverse(
            "usersec:hpcprojectinvitation-accept",
            kwargs={"hpcprojectinvitation": self.hpc_project_invitation.uuid},
        )
        good_users = [
            self.user_member2,
        ]
        not_so_good_users = [
            self.superuser,
        ]
        bad_users = [
            self.user_invited,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "GET",
            302,
            redirect_url=reverse(
                "usersec:hpcuser-overview",
            ),
        )
        self.assert_permissions_on_url(
            not_so_good_users,
            url,
            "GET",
            302,
            redirect_url=reverse("home"),
        )
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_project_invitation_reject_view_get(self):
        url = reverse(
            "usersec:hpcprojectinvitation-reject",
            kwargs={"hpcprojectinvitation": self.hpc_project_invitation.uuid},
        )
        good_users = [
            self.superuser,
            self.user_member2,
        ]
        bad_users = [
            self.user_invited,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(good_users, url, "GET", 200)
        self.assert_permissions_on_url(bad_users, url, "GET", 302, redirect_url=reverse("home"))

    def test_hpc_project_invitation_reject_view_post(self):
        url = reverse(
            "usersec:hpcprojectinvitation-reject",
            kwargs={"hpcprojectinvitation": self.hpc_project_invitation.uuid},
        )
        good_users = [
            self.superuser,
            self.user_member2,
        ]
        bad_users = [
            self.user_invited,
            self.user_owner,
            self.user_delegate,
            self.user_member,
            self.user_pending,
            self.user_hpcadmin,
            self.user_member_other_group,
            self.user,
        ]

        self.assert_permissions_on_url(
            good_users,
            url,
            "POST",
            302,
            redirect_url=reverse(
                "usersec:hpcuser-overview",
            ),
        )
        self.assert_permissions_on_url(bad_users, url, "POST", 302, redirect_url=reverse("home"))
