from django.conf import settings
from django.dispatch import receiver
from django_auth_ldap.backend import LDAPBackend, _LDAPUser, populate_user

# Username domains for primary and secondary LDAP backends
# Optional
LDAP_DOMAIN = getattr(settings, "AUTH_LDAP_USERNAME_DOMAIN", None)
# Required for LDAP2
LDAP2_DOMAIN = getattr(settings, "AUTH_LDAP2_USERNAME_DOMAIN", None)


# Primary LDAP backend
class PrimaryLDAPBackend(LDAPBackend):
    settings_prefix = "AUTH_LDAP_"

    def authenticate(self, request=None, username=None, password=None, **kwargs):
        domain = request.POST.get("domain") if request else None
        # Login with username@DOMAIN
        if LDAP_DOMAIN:
            if not domain == LDAP_DOMAIN:
                return None
            ldap_user = _LDAPUser(self, username=username.strip())
        # Login with username only
        else:
            if domain == "":
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
        domain = request.POST.get("domain")
        if not domain == LDAP2_DOMAIN:
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


# ------------------------------------------------------------------------------
# Handlers
# ------------------------------------------------------------------------------


def _ldap_auth_handler(user, ldap_user, **kwargs):
    """Signal for LDAP login handling"""

    phone = ldap_user.attrs.get("telephoneNumber")
    uid = ldap_user.attrs.get("uidNumber")
    first_name = ldap_user.attrs.get("givenName")
    last_name = ldap_user.attrs.get("sn")

    if phone:
        user.phone = phone[0]

    if uid:
        user.uid = uid[0]

    if first_name:
        user.first_name = first_name[0]

    if last_name:
        user.last_name = last_name[0]

    if hasattr(user, "ldap_username"):
        # Make domain in username uppercase
        if user.username.find("@") != -1 and user.username.split("@")[1].islower():
            u_split = user.username.split("@")
            user.username = u_split[0] + "@" + u_split[1].upper()
            user.save()

    # Save user name from first_name and last_name into name
    user.name = " ".join([user.first_name, user.last_name])
    user.save()


@receiver(populate_user, sender=PrimaryLDAPBackend)
def primary_ldap_auth_handler(user, ldap_user, **kwargs):  # noqa: W0613
    _ldap_auth_handler(user, ldap_user, **kwargs)


@receiver(populate_user, sender=SecondaryLDAPBackend)
def secondary_ldap_auth_handler(user, ldap_user, **kwargs):  # noqa: W0613
    _ldap_auth_handler(user, ldap_user, **kwargs)
