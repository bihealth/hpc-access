from django.test import TestCase, override_settings

from adminsec.ldap import LdapConnector


ENABLE_LDAP = True
ENABLE_LDAP_SECONDARY = True

AUTH_LDAP_SERVER_URI = "server_url"
AUTH_LDAP2_SERVER_URI = "server2_url"

AUTH_LDAP_BIND_DN = "cn=admin,ou=test,dc=institute"
AUTH_LDAP2_BIND_DN = "cn=admin,ou=test,dc=institute2"

AUTH_LDAP_BIND_PASSWORD = "passwd"
AUTH_LDAP2_BIND_PASSWORD = "passwd2"

INSTITUTE_EMAIL_DOMAINS = "example.com"
INSTITUTE2_EMAIL_DOMAINS = "example2.com"

AUTH_LDAP_USER_SEARCH_BASE = "dc=institute"
AUTH_LDAP2_USER_SEARCH_BASE = "dc=institute2"

AUTH_LDAP_USERNAME_DOMAIN = "DOMAIN"
AUTH_LDAP2_USERNAME_DOMAIN = "DOMAIN2"


LDAP_DEFAULT_MOCKS = {
    "ENABLE_LDAP": ENABLE_LDAP,
    "ENABLE_LDAP_SECONDARY": ENABLE_LDAP_SECONDARY,
    "AUTH_LDAP_SERVER_URI": AUTH_LDAP_SERVER_URI,
    "AUTH_LDAP2_SERVER_URI": AUTH_LDAP2_SERVER_URI,
    "AUTH_LDAP_BIND_DN": AUTH_LDAP_BIND_DN,
    "AUTH_LDAP2_BIND_DN": AUTH_LDAP2_BIND_DN,
    "AUTH_LDAP_BIND_PASSWORD": AUTH_LDAP_BIND_PASSWORD,
    "AUTH_LDAP2_BIND_PASSWORD": AUTH_LDAP2_BIND_PASSWORD,
    "INSTITUTE_EMAIL_DOMAINS": INSTITUTE_EMAIL_DOMAINS,
    "INSTITUTE2_EMAIL_DOMAINS": INSTITUTE2_EMAIL_DOMAINS,
    "AUTH_LDAP_USER_SEARCH_BASE": AUTH_LDAP_USER_SEARCH_BASE,
    "AUTH_LDAP2_USER_SEARCH_BASE": AUTH_LDAP2_USER_SEARCH_BASE,
    "AUTH_LDAP_USERNAME_DOMAIN": AUTH_LDAP_USERNAME_DOMAIN,
    "AUTH_LDAP2_USERNAME_DOMAIN": AUTH_LDAP2_USERNAME_DOMAIN,
}


USERNAME = "user"
USERNAME2 = "user2"

USER_MAIL_INSTITUTE = USERNAME + "@" + INSTITUTE_EMAIL_DOMAINS.split(",")[0]
USER_MAIL_INSTITUTE2 = USERNAME2 + "@" + INSTITUTE2_EMAIL_DOMAINS.split(",")[0]


class TestLdapConnector(TestCase):
    """Tests for LdapConnector."""

    @override_settings(**LDAP_DEFAULT_MOCKS)
    def setUp(self):
        super().setUp()

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
                },
            )

        self.ldap = LdapConnector(
            test_mode=True,
            test_setup_server1=setup_test_data_server1,
            test_setup_server2=setup_test_data_server2,
        )

    @override_settings(**LDAP_DEFAULT_MOCKS)
    def test_connect(self):
        self.assertTrue(self.ldap.connect())

    # @override_settings(**{**LDAP_DEFAULT_MOCKS, "ENABLE_LDAP_SECONDARY": False})
    @override_settings(**LDAP_DEFAULT_MOCKS)
    def test_get_ldap_username_domain_by_mail(self):
        self.ldap.connect()

        username, domain = self.ldap.get_ldap_username_domain_by_mail(USER_MAIL_INSTITUTE)

        self.assertEqual(username, USERNAME)
        self.assertEqual(domain, AUTH_LDAP_USERNAME_DOMAIN)

        username2, domain2 = self.ldap.get_ldap_username_domain_by_mail(USER_MAIL_INSTITUTE2)

        self.assertEqual(username2, USERNAME2)
        self.assertEqual(domain2, AUTH_LDAP2_USERNAME_DOMAIN)

    @override_settings(**LDAP_DEFAULT_MOCKS)
    def test_get_ldap_username_domain_by_mail_not_valid(self):
        self.ldap.connect()

        with self.assertRaisesRegex(Exception, "Email not valid"):
            self.ldap.get_ldap_username_domain_by_mail("some@other.mail")

    @override_settings(**LDAP_DEFAULT_MOCKS)
    def test_get_ldap_username_domain_by_mail_not_found(self):
        self.ldap.connect()

        with self.assertRaisesRegex(Exception, "No user found"):
            self.ldap.get_ldap_username_domain_by_mail(
                "some@" + INSTITUTE_EMAIL_DOMAINS.split(",")[0]
            )
