# Create your tasks here
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model

from adminsec.email import send_notification_storage_quota
from adminsec.ldap import LdapConnector
from config.celery import app
from usersec.models import HpcGroup, HpcProject, HpcQuotaStatus, HpcUser

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


def generate_quota_reports():
    return {
        "users": {o: o.generate_quota_report() for o in HpcUser.objects.all()},
        "projects": {o: o.generate_quota_report() for o in HpcProject.objects.all()},
        "groups": {o: o.generate_quota_report() for o in HpcGroup.objects.all()},
    }


@app.task(bin=True)
def send_quota_email(_self):
    if not settings.SEND_QUOTA_EMAILS:
        return

    reports = generate_quota_reports()

    for data in reports.values():
        for hpc_obj, report in data.items():
            if any([not s == HpcQuotaStatus.GREEN for s in report["status"].values()]):
                send_notification_storage_quota(hpc_obj, report)


@app.task(bind=True)
def sync_ldap(_self, write=False, verbose=False):
    _sync_ldap(write, verbose)
