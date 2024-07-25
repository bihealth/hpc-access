from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from test_plus import TestCase

from adminsec.constants import TIER_USER_HOME
from adminsec.ldap import LdapConnector
from adminsec.tasks import (
    _generate_quota_reports,
    _send_quota_email,
    _sync_ldap,
    clean_db_of_hpc_objects,
    disable_users_without_consent,
    send_quota_email_red,
    send_quota_email_yellow,
)
from adminsec.tests.test_ldap import (
    AUTH_LDAP2_BIND_DN,
    AUTH_LDAP2_BIND_PASSWORD,
    AUTH_LDAP2_USER_SEARCH_BASE,
    AUTH_LDAP2_USERNAME_DOMAIN,
    AUTH_LDAP_BIND_DN,
    AUTH_LDAP_BIND_PASSWORD,
    AUTH_LDAP_USER_SEARCH_BASE,
    AUTH_LDAP_USERNAME_DOMAIN,
    LDAP_DEFAULT_MOCKS,
    USER_MAIL_INSTITUTE,
    USER_MAIL_INSTITUTE2,
    USERNAME,
    USERNAME2,
)
from usersec.models import (
    OBJECT_STATUS_ACTIVE,
    OBJECT_STATUS_EXPIRED,
    HpcGroup,
    HpcGroupChangeRequest,
    HpcGroupCreateRequest,
    HpcGroupDeleteRequest,
    HpcGroupInvitation,
    HpcProject,
    HpcProjectChangeRequest,
    HpcProjectCreateRequest,
    HpcProjectDeleteRequest,
    HpcProjectInvitation,
    HpcQuotaStatus,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
)
from usersec.tests.factories import (
    HpcGroupChangeRequestFactory,
    HpcGroupCreateRequestFactory,
    HpcGroupDeleteRequestFactory,
    HpcGroupFactory,
    HpcGroupInvitationFactory,
    HpcProjectChangeRequestFactory,
    HpcProjectCreateRequestFactory,
    HpcProjectDeleteRequestFactory,
    HpcProjectFactory,
    HpcProjectInvitationFactory,
    HpcUserChangeRequestFactory,
    HpcUserCreateRequestFactory,
    HpcUserDeleteRequestFactory,
    HpcUserFactory,
    TermsAndConditionsFactory,
)

LDAP_OTHER_DOMAIN_MOCK = {**LDAP_DEFAULT_MOCKS, "AUTH_LDAP2_USERNAME_DOMAIN": "OTHER_DOMAIN"}


User = get_user_model()


class TestSyncLdap(TestCase):
    """Tests for sync_ldap."""

    @override_settings(**LDAP_DEFAULT_MOCKS)
    def setUp(self):
        super().setUp()

        self.user1 = self.make_user(f"{USERNAME}@{AUTH_LDAP_USERNAME_DOMAIN}")
        self.user1.email = "user1@wrong.mail"
        self.user1.is_active = False
        self.user1.save()

        self.user2 = self.make_user(f"{USERNAME2}@{AUTH_LDAP2_USERNAME_DOMAIN}")
        self.user2.email = "user2@wrong.mail"
        self.user2.is_active = False
        self.user2.save()

        # Prevent additional users from being created; they are not required here
        self.hpcuser1 = HpcUserFactory(user=self.user1, primary_group=None, creator=None)
        self.hpcuser2 = HpcUserFactory(user=self.user2, primary_group=None, creator=None)

        def setup_test_data_server1(connection):
            connection.strategy.add_entry(
                AUTH_LDAP_BIND_DN,
                {
                    "sAMAccountName": "admin",
                    "userPassword": AUTH_LDAP_BIND_PASSWORD,
                },
            )
            connection.strategy.add_entry(
                "cn=user,ou=test," + AUTH_LDAP_USER_SEARCH_BASE,
                {
                    "objectclass": "person",
                    "mail": USER_MAIL_INSTITUTE,
                    "sAMAccountName": USERNAME,
                    "userAccountControl": 512,
                    "telephoneNumber": "54321",
                    "uidNumber": 101,
                    "givenName": "Jane",
                    "sn": "Joe",
                },
            )

        def setup_test_data_server2(connection):
            connection.strategy.add_entry(
                AUTH_LDAP2_BIND_DN,
                {
                    "sAMAccountName": "admin",
                    "userPassword": AUTH_LDAP2_BIND_PASSWORD,
                },
            )
            connection.strategy.add_entry(
                "cn=user,ou=test," + AUTH_LDAP2_USER_SEARCH_BASE,
                {
                    "objectclass": "person",
                    "mail": USER_MAIL_INSTITUTE2,
                    "sAMAccountName": USERNAME2,
                    "userAccountControl": 512,
                    "telephoneNumber": "12345",
                    "uidNumber": 102,
                    "givenName": "John",
                    "sn": "Doe",
                },
            )

        self.ldap = LdapConnector(
            test_mode=True,
            test_setup_server1=setup_test_data_server1,
            test_setup_server2=setup_test_data_server2,
        )

    @override_settings(**LDAP_DEFAULT_MOCKS)
    def test__sync_ldap_sanity(self):
        _sync_ldap(ldapcon=self.ldap)

    @override_settings(**LDAP_DEFAULT_MOCKS)
    def test__sync_ldap(self):
        exception_count = _sync_ldap(ldapcon=self.ldap, write=True)

        self.assertEqual(exception_count, {})

        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.hpcuser1.refresh_from_db()
        self.hpcuser2.refresh_from_db()

        self.assertEqual(self.user1.first_name, "Jane")
        self.assertEqual(self.user1.last_name, "Joe")
        self.assertEqual(self.user1.email, USER_MAIL_INSTITUTE)
        self.assertEqual(self.user1.phone, "54321")
        self.assertEqual(self.user1.uid, 101)
        self.assertEqual(self.user1.name, "Jane Joe")
        self.assertTrue(self.user1.is_active)
        self.assertEqual(self.hpcuser1.status, "ACTIVE")

        self.assertEqual(self.user2.first_name, "John")
        self.assertEqual(self.user2.last_name, "Doe")
        self.assertEqual(self.user2.email, USER_MAIL_INSTITUTE2)
        self.assertEqual(self.user2.phone, "12345")
        self.assertEqual(self.user2.uid, 102)
        self.assertEqual(self.user2.name, "John Doe")
        self.assertTrue(self.user2.is_active)
        self.assertEqual(self.hpcuser2.status, "ACTIVE")

    @override_settings(**LDAP_OTHER_DOMAIN_MOCK)
    def test__sync_ldap_invalid_domain(self):
        exception_count = _sync_ldap(ldapcon=self.ldap, write=True)

        self.assertEqual(
            exception_count,
            {f"Domain {AUTH_LDAP2_USERNAME_DOMAIN} not valid. Maybe LDAP not activated?": 1},
        )

        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.hpcuser1.refresh_from_db()
        self.hpcuser2.refresh_from_db()

        self.assertEqual(self.user1.first_name, "Jane")
        self.assertEqual(self.user1.last_name, "Joe")
        self.assertEqual(self.user1.email, USER_MAIL_INSTITUTE)
        self.assertEqual(self.user1.phone, "54321")
        self.assertEqual(self.user1.uid, 101)
        self.assertEqual(self.user1.name, "Jane Joe")
        self.assertTrue(self.user1.is_active)
        self.assertEqual(self.hpcuser1.status, "ACTIVE")

        self.assertEqual(self.user2.first_name, "")
        self.assertEqual(self.user2.last_name, "")
        self.assertEqual(self.user2.email, "user2@wrong.mail")
        self.assertEqual(self.user2.phone, None)
        self.assertEqual(self.user2.uid, None)
        self.assertEqual(self.user2.name, None)
        self.assertFalse(self.user2.is_active)
        self.assertEqual(self.hpcuser2.status, "INITIAL")

    @override_settings(**LDAP_DEFAULT_MOCKS)
    def test__sync_ldap_invalid_no_user_found(self):
        self.user1.username = f"other_user@{AUTH_LDAP_USERNAME_DOMAIN}"
        self.user1.save()

        exception_count = _sync_ldap(ldapcon=self.ldap, write=True)

        self.assertEqual(
            exception_count,
            {f"No user found for username: other_user@{AUTH_LDAP_USERNAME_DOMAIN}": 1},
        )

        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.hpcuser1.refresh_from_db()
        self.hpcuser2.refresh_from_db()

        self.assertEqual(self.user1.first_name, "")
        self.assertEqual(self.user1.last_name, "")
        self.assertEqual(self.user1.email, "user1@wrong.mail")
        self.assertEqual(self.user1.phone, None)
        self.assertEqual(self.user1.uid, None)
        self.assertEqual(self.user1.name, None)
        self.assertFalse(self.user1.is_active)
        self.assertEqual(self.hpcuser1.status, "INITIAL")

        self.assertEqual(self.user2.first_name, "John")
        self.assertEqual(self.user2.last_name, "Doe")
        self.assertEqual(self.user2.email, USER_MAIL_INSTITUTE2)
        self.assertEqual(self.user2.phone, "12345")
        self.assertEqual(self.user2.uid, 102)
        self.assertEqual(self.user2.name, "John Doe")
        self.assertTrue(self.user2.is_active)
        self.assertEqual(self.hpcuser2.status, "ACTIVE")


class TestSendQuotaEmail(TestCase):
    """Tests for _send_quota_email."""

    def setUp(self):
        # Superuser
        self.superuser = self.make_user("superuser")
        self.superuser.is_superuser = True
        self.superuser.save()

        # HPC Admin
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()

        # Init default user
        self.user = self.make_user("user@CHARITE")
        self.user.name = "John Doe"
        self.user.email = "user@example.com"
        self.user.save()

        # Create group and owner
        self.user_owner = self.make_user("owner")
        self.user_owner.email = "owner@example.com"
        self.user_owner.name = "AG Owner"
        self.user_owner.save()

        self.hpc_group = HpcGroupFactory(
            resources_requested={"work": 20},
            resources_used={"work": 10},  # 50% used
            folders={"work": "/data/work/group"},
        )
        self.hpc_owner = HpcUserFactory(
            user=self.user_owner,
            primary_group=self.hpc_group,
            creator=self.user_hpcadmin,
            resources_requested={TIER_USER_HOME: 20},
            resources_used={TIER_USER_HOME: 20},  # 100% used
        )
        self.hpc_group.owner = self.hpc_owner
        self.hpc_group.save()

        self.user_member = self.make_user("member")
        self.user_member.name = "AG Member"
        self.user_member.email = "member@example.com"
        self.user_member.save()

        self.hpc_member = HpcUserFactory(
            user=self.user_member,
            primary_group=self.hpc_group,
            creator=self.user_hpcadmin,
            resources_requested={TIER_USER_HOME: 20},
            resources_used={TIER_USER_HOME: 18},  # 90% used
        )

        # Create project
        self.hpc_project = HpcProjectFactory(
            group=self.hpc_group,
            resources_requested={"work": 20, "scratch": 20},
            resources_used={"work": 18, "scratch": 20},  # 90% used, 100% used
            folders={"work": "/data/work/project", "scratch": "/data/scratch/project"},
        )
        self.hpc_project.members.add(self.hpc_owner)
        self.hpc_project.get_latest_version().members.add(self.hpc_owner)

    def test_generate_quota_reports(self):
        expected = {
            "users": {o: o.generate_quota_report() for o in [self.hpc_owner, self.hpc_member]},
            "projects": {o: o.generate_quota_report() for o in [self.hpc_project]},
            "groups": {o: o.generate_quota_report() for o in [self.hpc_group]},
        }
        reports = _generate_quota_reports()
        self.assertEqual(reports, expected)

    @override_settings(SEND_QUOTA_EMAILS=True)
    def test__send_quota_email_red(self):
        _send_quota_email(HpcQuotaStatus.RED)
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(SEND_QUOTA_EMAILS=True)
    def test__send_quota_email_red_with_delegate(self):
        self.hpc_project.delegate = self.hpc_member
        self.hpc_project.members.add(self.hpc_member)
        self.hpc_project.get_latest_version().members.add(self.hpc_member)
        self.hpc_project.save()
        _send_quota_email(HpcQuotaStatus.RED)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(SEND_QUOTA_EMAILS=True)
    def test__send_quota_email_yellow(self):
        _send_quota_email(HpcQuotaStatus.YELLOW)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(SEND_QUOTA_EMAILS=True)
    def test__send_quota_email_status_green(self):
        _send_quota_email(HpcQuotaStatus.GREEN)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(SEND_QUOTA_EMAILS=True)
    def test_send_quota_email_red(self):
        send_quota_email_red()
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(SEND_QUOTA_EMAILS=True)
    def test_send_quota_email_yellow(self):
        send_quota_email_yellow()
        self.assertEqual(len(mail.outbox), 1)


class DisableUsersWithoutConsent(TestCase):
    """Tests for disable_users_without_consent."""

    def setUp(self):
        # Superuser
        self.superuser = self.make_user("superuser")
        self.superuser.is_superuser = True
        self.superuser.save()

        # HPC Admin
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()

        self.user1 = self.make_user(f"{USERNAME}@{AUTH_LDAP_USERNAME_DOMAIN}")
        self.user1.email = "user1@example.mail"
        self.user1.is_active = True
        self.user1.consented_to_terms = False
        self.user1.save()

        self.user2 = self.make_user(f"{USERNAME2}@{AUTH_LDAP2_USERNAME_DOMAIN}")
        self.user2.email = "user2@example.mail"
        self.user2.is_active = True
        self.user2.consented_to_terms = False
        self.user2.save()

        self.hpc_user1 = HpcUserFactory(
            user=self.user1,
            primary_group=None,
            creator=self.user_hpcadmin,
            status=OBJECT_STATUS_ACTIVE,
        )

    def test_disable_users_without_consent_all_not_consented_grace_reached(self):
        self.terms_all = TermsAndConditionsFactory(
            date_published=timezone.now() - timedelta(days=40)
        )

        self.assertEqual(User.objects.filter(is_active=False).count(), 0)

        disable_users_without_consent()

        self.assertEqual(User.objects.filter(is_active=False).count(), 2)
        self.hpc_user1.refresh_from_db()
        self.assertEqual(self.hpc_user1.status, OBJECT_STATUS_EXPIRED)
        self.assertEqual(self.hpc_user1.login_shell, "/usr/sbin/nologin")

    def test_disable_users_without_consent_all_consented_grace_reached(self):
        self.terms_all = TermsAndConditionsFactory(
            date_published=timezone.now() - timedelta(days=40)
        )
        self.user1.consented_to_terms = True
        self.user1.save()
        self.user2.consented_to_terms = True
        self.user2.save()

        self.assertEqual(User.objects.filter(is_active=False).count(), 0)

        disable_users_without_consent()

        self.assertEqual(User.objects.filter(is_active=False).count(), 0)
        self.hpc_user1.refresh_from_db()
        self.assertEqual(self.hpc_user1.status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(self.hpc_user1.login_shell, "/usr/bin/bash")

    def test_disable_users_without_consent_not_consented_grace_not_reached(self):
        self.terms_all = TermsAndConditionsFactory(
            date_published=timezone.now() - timedelta(days=10)
        )

        self.assertEqual(User.objects.filter(is_active=False).count(), 0)

        disable_users_without_consent()

        self.assertEqual(User.objects.filter(is_active=False).count(), 0)


class CleanDbOfHpcObjects(TestCase):
    """Tests for clean_db_of_hpc_objects."""

    def setUp(self):
        # Superuser
        self.superuser = self.make_user("superuser")
        self.superuser.is_superuser = True
        self.superuser.save()

        # HPC Admin
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()

        # Init default user
        self.user = self.make_user("user@CHARITE")
        self.user.name = "John Doe"
        self.user.email = "user@example.com"
        self.user.consented_to_terms = True
        self.user.save()

        # Create group and owner
        self.user_owner = self.make_user("owner")
        self.user_owner.email = "owner@example.com"
        self.user_owner.name = "AG Owner"
        self.user_owner.save()

        self.hpc_group = HpcGroupFactory(creator=self.user_hpcadmin)
        self.hpc_owner = HpcUserFactory(
            user=self.user_owner, primary_group=self.hpc_group, creator=self.user_hpcadmin
        )
        self.hpc_group.owner = self.hpc_owner
        self.hpc_group.save()

        self.user_member = self.make_user("member")
        self.user_member.name = "AG Member"
        self.user_member.email = "member@example.com"
        self.user_member.save()

        self.hpc_member = HpcUserFactory(
            user=self.user_member, primary_group=self.hpc_group, creator=self.user_hpcadmin
        )

        # Create project
        self.hpc_project = HpcProjectFactory(group=self.hpc_group, creator=self.user_hpcadmin)
        self.hpc_project.members.add(self.hpc_owner)
        self.hpc_project.get_latest_version().members.add(self.hpc_owner)

        # Create group requests
        HpcGroupCreateRequestFactory(requester=self.user)
        HpcGroupChangeRequestFactory(requester=self.user_owner, group=self.hpc_group)
        HpcGroupDeleteRequestFactory(requester=self.user_owner, group=self.hpc_group)

        # Create project requests
        self.hpc_project_create_request = HpcProjectCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group
        )
        HpcProjectChangeRequestFactory(requester=self.user_owner, project=self.hpc_project)
        HpcProjectDeleteRequestFactory(requester=self.user_owner, project=self.hpc_project)

        # Create user requests
        self.hpc_user_create_request = HpcUserCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group
        )
        HpcUserChangeRequestFactory(requester=self.user_owner, user=self.hpc_owner)
        HpcUserDeleteRequestFactory(requester=self.user_owner, user=self.hpc_owner)

        # Create invitations
        HpcProjectInvitationFactory(
            project=self.hpc_project,
            user=self.hpc_member,
            hpcprojectcreaterequest=self.hpc_project_create_request,
        )
        HpcGroupInvitationFactory(hpcusercreaterequest=self.hpc_user_create_request)

    def test_clean_db_of_hpc_objects(self):
        self.assertEqual(HpcUser.objects.count(), 2)
        self.assertEqual(HpcGroup.objects.count(), 1)
        self.assertEqual(HpcProject.objects.count(), 1)
        self.assertEqual(HpcGroupCreateRequest.objects.count(), 1)
        self.assertEqual(HpcGroupChangeRequest.objects.count(), 1)
        self.assertEqual(HpcGroupDeleteRequest.objects.count(), 1)
        self.assertEqual(HpcProjectCreateRequest.objects.count(), 1)
        self.assertEqual(HpcProjectChangeRequest.objects.count(), 1)
        self.assertEqual(HpcProjectDeleteRequest.objects.count(), 1)
        self.assertEqual(HpcUserCreateRequest.objects.count(), 1)
        self.assertEqual(HpcUserChangeRequest.objects.count(), 1)
        self.assertEqual(HpcProjectInvitation.objects.count(), 1)
        self.assertEqual(HpcGroupInvitation.objects.count(), 1)
        self.assertEqual(User.objects.count(), 5)

        ret = clean_db_of_hpc_objects()

        self.assertTrue(ret, [self.user.username])
        self.assertEqual(HpcUser.objects.count(), 0)
        self.assertEqual(HpcGroup.objects.count(), 0)
        self.assertEqual(HpcProject.objects.count(), 0)
        self.assertEqual(HpcGroupCreateRequest.objects.count(), 0)
        self.assertEqual(HpcGroupChangeRequest.objects.count(), 0)
        self.assertEqual(HpcGroupDeleteRequest.objects.count(), 0)
        self.assertEqual(HpcProjectCreateRequest.objects.count(), 0)
        self.assertEqual(HpcProjectChangeRequest.objects.count(), 0)
        self.assertEqual(HpcProjectDeleteRequest.objects.count(), 0)
        self.assertEqual(HpcUserCreateRequest.objects.count(), 0)
        self.assertEqual(HpcUserChangeRequest.objects.count(), 0)
        self.assertEqual(HpcProjectInvitation.objects.count(), 0)
        self.assertEqual(HpcGroupInvitation.objects.count(), 0)
        self.assertEqual(User.objects.count(), 2)
