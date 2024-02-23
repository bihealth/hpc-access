from django.contrib.auth import get_user_model
from django.test import override_settings
from test_plus import TestCase

from adminsec.ldap import LdapConnector
from adminsec.tasks import _sync_ldap
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
from usersec.tests.factories import HpcUserFactory

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
