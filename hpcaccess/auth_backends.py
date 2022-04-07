from django.conf import settings
from django.dispatch import receiver
from django_auth_ldap.backend import LDAPBackend, _LDAPUser, populate_user

# Username domains for primary and secondary LDAP backends
# Optional
from adminsec.views import django_to_hpc_username
from usersec.models import HpcUser, OBJECT_STATUS_ACTIVE

LDAP_DOMAIN = getattr(settings, "AUTH_LDAP_USERNAME_DOMAIN", None)
# Required for LDAP2
LDAP2_DOMAIN = getattr(settings, "AUTH_LDAP2_USERNAME_DOMAIN", None)


# Primary LDAP backend
class PrimaryLDAPBackend(LDAPBackend):
    settings_prefix = "AUTH_LDAP_"

    def authenticate(self, request=None, username=None, password=None, **kwargs):
        # Login with username@DOMAIN
        if LDAP_DOMAIN:
            if username.find("@") == -1 or username.strip().split("@")[1].upper() != LDAP_DOMAIN:
                return None
            ldap_user = _LDAPUser(self, username=username.split("@")[0].strip())
        # Login with username only
        else:
            if username.find("@") != -1:
                return None
            ldap_user = _LDAPUser(self, username=username.strip())
        user = ldap_user.authenticate(password)
        return user

    def ldap_to_django_username(self, username):
        """Override LDAPBackend function to get the username with domain"""
        return (username + "@" + LDAP_DOMAIN) if LDAP_DOMAIN else username

    def django_to_ldap_username(self, username):
        """Override LDAPBackend function to get the real LDAP username"""
        return username.split("@")[0] if LDAP_DOMAIN else username


# Secondary AD backend
class SecondaryLDAPBackend(LDAPBackend):
    settings_prefix = "AUTH_LDAP2_"

    def authenticate(self, request=None, username=None, password=None, **kwargs):
        if username.find("@") == -1 or username.split("@")[1].upper() != LDAP2_DOMAIN:
            return None

        ldap_user = _LDAPUser(self, username=username.split("@")[0].strip())
        user = ldap_user.authenticate(password)
        return user

    def ldap_to_django_username(self, username):
        """Override LDAPBackend function to get the username with domain"""
        return username + "@" + LDAP2_DOMAIN

    def django_to_ldap_username(self, username):
        """Override LDAPBackend function to get the real LDAP username"""
        return username.split("@")[0]


@receiver(populate_user, sender=PrimaryLDAPBackend)
def primary_ldap_auth_handler(user, ldap_user, **kwargs):  # noqa: W0613
    phone = ldap_user.attrs.get("telephoneNumber")

    if phone:
        user.phone = phone[0]

    if not user.hpcuser_user.exists():
        username = django_to_hpc_username(user.username)
        hpcuser = HpcUser.objects.filter(username=username)

        if hpcuser.count() == 1:
            hpcuser = hpcuser.first()
            hpcuser.user = user
            hpcuser.status = OBJECT_STATUS_ACTIVE
            hpcuser.save_with_version()


@receiver(populate_user, sender=SecondaryLDAPBackend)
def secondary_ldap_auth_handler(user, ldap_user, **kwargs):  # noqa: W0613
    phone = ldap_user.attrs.get("telephoneNumber")

    if phone:
        user.phone = phone[0]

    if not user.hpcuser_user.exists():
        username = django_to_hpc_username(user.username)
        hpcuser = HpcUser.objects.filter(username=username)

        if hpcuser.count() == 1:
            hpcuser = hpcuser.first()
            hpcuser.user = user
            hpcuser.status = OBJECT_STATUS_ACTIVE
            hpcuser.save_with_version()
