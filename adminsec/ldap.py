from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import ldap3


class LdapConnector:
    """Connect to the two LDAPs and provide some search functions."""

    connection1 = None
    connection2 = None

    def __init__(self, test_mode=False, test_setup_server1=None, test_setup_server2=None):
        self.test_mode = test_mode
        self.test_setup_server1 = test_setup_server1
        self.test_setup_server2 = test_setup_server2

    def connect(self):
        # Open LDAP connections and bind
        test_mode = {}

        if self.test_mode:
            test_mode["client_strategy"] = ldap3.MOCK_SYNC

        if settings.ENABLE_LDAP:
            server1 = ldap3.Server(settings.AUTH_LDAP_SERVER_URI)

            self.connection1 = ldap3.Connection(
                server1,
                user=settings.AUTH_LDAP_BIND_DN,
                password=settings.AUTH_LDAP_BIND_PASSWORD,
                **test_mode
            )

            if self.test_mode:
                self.test_setup_server1(self.connection1)

            if not self.connection1.bind():
                raise ConnectionError("Could not connect to LDAP")

        if settings.ENABLE_LDAP_SECONDARY:
            server2 = ldap3.Server(settings.AUTH_LDAP2_SERVER_URI)
            self.connection2 = ldap3.Connection(
                server2,
                user=settings.AUTH_LDAP2_BIND_DN,
                password=settings.AUTH_LDAP2_BIND_PASSWORD,
                **test_mode
            )

            if self.test_mode:
                self.test_setup_server2(self.connection2)

            if not self.connection2.bind():
                raise ConnectionError("Could not connect to LDAP2")

        return True

    def get_ldap_username_domain_by_mail(self, mail):
        """Load user information from a given email."""

        email_domains = []
        email_domains2 = []

        if settings.ENABLE_LDAP:
            email_domains = settings.INSTITUTE_EMAIL_DOMAINS.split(",")

        if settings.ENABLE_LDAP_SECONDARY:
            email_domains2 = settings.INSTITUTE2_EMAIL_DOMAINS.split(",")

        if mail.split("@")[1].lower() in email_domains:
            connection = self.connection1

            if not connection:
                raise ImproperlyConfigured("LDAP not activated but required for request.")

            search_base = settings.AUTH_LDAP_USER_SEARCH_BASE
            domain = settings.AUTH_LDAP_USERNAME_DOMAIN

        elif mail.split("@")[1].lower() in email_domains2:
            connection = self.connection2

            if not connection:
                raise ImproperlyConfigured("LDAP2 not activated but required for request.")

            search_base = settings.AUTH_LDAP2_USER_SEARCH_BASE
            domain = settings.AUTH_LDAP2_USERNAME_DOMAIN

        else:
            raise ImproperlyConfigured("Email not valid")

        search_params = {
            "search_base": search_base,
            "search_filter": "(&(objectclass=person)(mail={}))".format(mail),
            "attributes": ["sAMAccountName"],
        }

        if not connection.search(**search_params):
            raise Exception("No user found")

        if not len(connection.entries) == 1:
            raise Exception("Less or more than one user found")

        if "sAMAccountName" not in connection.entries[0]:
            raise Exception("Username attribute (sAMAccountName) not found!")

        return connection.entries[0]["sAMAccountName"][0], domain
