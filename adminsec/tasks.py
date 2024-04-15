# Create your tasks here
from collections import defaultdict

from django.contrib.auth import get_user_model

from adminsec.ldap import LdapConnector
from config.celery import app

User = get_user_model()


def _sync_ldap(write=False, verbose=False, ldapcon=None):
    if not ldapcon:
        ldapcon = LdapConnector(logging=verbose)

    ldapcon.connect()

    exception_count = defaultdict(int)

    for user in User.objects.filter(
        is_superuser=False,
        is_staff=False,
        is_hpcadmin=False,
    ):
        try:
            userinfo = ldapcon.get_user_info(user.username)
            userAccountControl = userinfo.userAccountControl
            phone = userinfo.telephoneNumber
            uid = userinfo.uidNumber
            first_name = userinfo.givenName
            last_name = userinfo.sn
            mail = userinfo.mail
            disabled = True

            if userAccountControl:
                disabled = bool(int(userinfo.userAccountControl.value) & 2)

            if last_name:
                user.last_name = last_name[0].strip()

            if first_name:
                user.first_name = first_name[0].strip()

            if mail:
                user.email = mail[0]

            if phone:
                user.phone = phone[0]

            if uid:
                user.uid = uid[0]

            user.name = " ".join([user.first_name, user.last_name])
            user.is_active = not disabled

            if user.hpcuser_user.count():
                hpcuser = user.hpcuser_user.first()
                hpcuser.status = "EXPIRED" if disabled else "ACTIVE"

                if write:
                    hpcuser.save()

            if write:
                user.save()

        except Exception as e:
            exception_count[str(e)] += 1
            continue

    return exception_count


@app.task(bind=True)
def sync_ldap(_self, write=False, verbose=False):
    _sync_ldap(write, verbose)
