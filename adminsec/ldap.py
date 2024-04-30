import logging as _logging

import ldap3
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = _logging.getLogger("ldap_connector_logger")


class LdapConnector:
    """Connect to the two LDAPs and provide some search functions."""

    connection1 = None
    connection2 = None

    def __init__(
        self, test_mode=False, test_setup_server1=None, test_setup_server2=None, logging=False
    ):
        self.test_mode = test_mode
        self.test_setup_server1 = test_setup_server1
        self.test_setup_server2 = test_setup_server2
        if logging:
            logger.setLevel(_logging.DEBUG)
        else:
            logger.setLevel(_logging.CRITICAL)

    def connect(self):
        # Open LDAP connections and bind
        test_mode = {}

        if self.test_mode:
            logger.debug("LDAP test mode enabled")
            test_mode["client_strategy"] = ldap3.MOCK_SYNC

        if settings.ENABLE_LDAP:
            logger.debug("LDAP enabled")
            server1 = ldap3.Server(settings.AUTH_LDAP_SERVER_URI)

            logger.debug("Connecting to LDAP server: %s", settings.AUTH_LDAP_SERVER_URI)
            self.connection1 = ldap3.Connection(
                server1,
                user=settings.AUTH_LDAP_BIND_DN,
                password=settings.AUTH_LDAP_BIND_PASSWORD,
                **test_mode,
            )

            if self.test_mode:
                logger.debug("LDAP test mode: setting up server 1")
                self.test_setup_server1(self.connection1)

            if not self.connection1.bind():
                msg = "Could not connect to LDAP"
                logger.error(msg)
                raise ConnectionError(msg)

        if settings.ENABLE_LDAP_SECONDARY:
            logger.debug("LDAP2 enabled")
            server2 = ldap3.Server(settings.AUTH_LDAP2_SERVER_URI)

            logger.debug("Connecting to LDAP2 server: %s", settings.AUTH_LDAP2_SERVER_URI)
            self.connection2 = ldap3.Connection(
                server2,
                user=settings.AUTH_LDAP2_BIND_DN,
                password=settings.AUTH_LDAP2_BIND_PASSWORD,
                **test_mode,
            )

            if self.test_mode:
                logger.debug("LDAP test mode: setting up server 2")
                self.test_setup_server2(self.connection2)

            if not self.connection2.bind():
                msg = "Could not connect to LDAP2"
                logger.error(msg)
                raise ConnectionError(msg)

        return True

    def get_ldap_username_domain_by_mail(self, mail):
        """Load user information from a given email."""

        email_domains = []
        email_domains2 = []

        if settings.ENABLE_LDAP:
            email_domains = settings.INSTITUTE_EMAIL_DOMAINS.split(",")
            logger.debug("Email domains: %s", email_domains)

        if settings.ENABLE_LDAP_SECONDARY:
            email_domains2 = settings.INSTITUTE2_EMAIL_DOMAINS.split(",")
            logger.debug("Email domains 2: %s", email_domains2)

        if mail.split("@")[1].lower() in email_domains:
            connection = self.connection1

            if not connection:
                msg = "LDAP not activated but required for request."
                logger.error(msg)
                raise ImproperlyConfigured(msg)

            search_base = settings.AUTH_LDAP_USER_SEARCH_BASE
            domain = settings.AUTH_LDAP_USERNAME_DOMAIN

        elif mail.split("@")[1].lower() in email_domains2:
            connection = self.connection2

            if not connection:
                msg = "LDAP2 not activated but required for request."
                logger.error(msg)
                raise ImproperlyConfigured(msg)

            search_base = settings.AUTH_LDAP2_USER_SEARCH_BASE
            domain = settings.AUTH_LDAP2_USERNAME_DOMAIN

        else:
            logger.error("Email %s not valid" % mail)
            raise ImproperlyConfigured("Email %s not valid" % mail)

        search_params = {
            "search_base": search_base,
            "search_filter": "(&(objectclass=person)(mail={}))".format(mail),
            "attributes": ["sAMAccountName"],
        }

        logger.debug("Searching for user with email: %s" % mail)
        logger.debug("Using search params: %s" % search_params)

        if not connection.search(**search_params):
            msg = "No user found"
            logger.error(msg)
            raise Exception(msg)

        if not len(connection.entries) == 1:
            msg = "Less or more than one user found"
            logger.error(msg)
            raise Exception(msg)

        if "sAMAccountName" not in connection.entries[0]:
            msg = "Username attribute (sAMAccountName) not found!"
            logger.error(msg)
            raise Exception(msg)

        return connection.entries[0]["sAMAccountName"].value, domain

    def get_user_info(self, username):
        """Load usr information for a given username."""

        try:
            username, domain = username.split("@")
        except ValueError as err:
            msg = "Username must be in the form username@DOMAIN (violator: '%s')" % username
            logger.error(msg)
            raise ValueError(msg) from err

        if settings.ENABLE_LDAP and domain == settings.AUTH_LDAP_USERNAME_DOMAIN:
            connection = self.connection1

            if not connection:
                msg = "LDAP connection not available."
                logger.error(msg)
                raise ImproperlyConfigured(msg)

            search_base = settings.AUTH_LDAP_USER_SEARCH_BASE

        elif settings.ENABLE_LDAP_SECONDARY and domain == settings.AUTH_LDAP2_USERNAME_DOMAIN:
            connection = self.connection2

            if not connection:
                msg = "LDAP2 connection not available."
                logger.error(msg)
                raise ImproperlyConfigured(msg)

            search_base = settings.AUTH_LDAP2_USER_SEARCH_BASE

        else:
            msg = "Domain %s not valid. Maybe LDAP not activated?" % domain
            logger.error(msg)
            raise ImproperlyConfigured(msg)

        search_params = {
            "search_base": search_base,
            "search_filter": "(&(objectclass=person)(sAMAccountName={}))".format(username),
            "attributes": [
                "mail",
                "displayName",
                "givenName",
                "sn",
                "userAccountControl",
                "telephoneNumber",
                "uidNumber",
            ],
        }

        if not connection.search(**search_params):
            msg = "No user found for username: %s@%s" % (username, domain)
            logger.error(msg)
            raise Exception(msg)

        if not len(connection.entries) == 1:
            msg = "Less or more than one user found for username: %s@%s" % (username, domain)
            logger.error(msg)
            raise Exception(msg)

        logger.debug("User found for username: %s@%s" % (username, domain))

        return connection.entries[0]
