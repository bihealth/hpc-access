# Create your tasks here
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from adminsec.email import send_notification_storage_quota
from adminsec.ldap import LdapConnector
from config.celery import app
from usersec.models import (
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
    HpcUserDeleteRequest,
    TermsAndConditions,
)

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


def _generate_quota_reports():
    return {
        "users": {o: o.generate_quota_report() for o in HpcUser.objects.all()},
        "projects": {o: o.generate_quota_report() for o in HpcProject.objects.all()},
        "groups": {o: o.generate_quota_report() for o in HpcGroup.objects.all()},
    }


@app.task(bind=True)
def send_quota_email(_self):
    if not settings.SEND_QUOTA_EMAILS:
        return

    reports = _generate_quota_reports()

    for data in reports.values():
        for hpc_obj, report in data.items():
            if any([not s == HpcQuotaStatus.GREEN for s in report["status"].values()]):
                send_notification_storage_quota(hpc_obj, report)


@transaction.atomic
@app.task(bind=True)
def disable_users_without_consent(_self):
    terms = TermsAndConditions.objects.filter(date_published__isnull=False)
    if not terms.exists():
        return
    if (
        terms.first().date_published + timezone.timedelta(days=settings.CONSENT_GRACE_PERIOD)
        > timezone.now()
    ):
        return
    users = (
        User.objects.filter(consented_to_terms=False)
        .exclude(is_hpcadmin=True)
        .exclude(is_superuser=True)
        .exclude(is_staff=True)
    )
    for user in users:
        user.is_active = False
        user.save()
        try:
            hpcuser = HpcUser.objects.get(user=user)
            hpcuser.status = OBJECT_STATUS_EXPIRED
            hpcuser.login_shell = "/usr/sbin/nologin"
            hpcuser.save()
        except HpcUser.DoesNotExist:
            continue


@app.task(bind=True)
def sync_ldap(_self, write=False, verbose=False):
    _sync_ldap(write, verbose)


@transaction.atomic
def clean_db_of_hpc_objects():
    hpc_object_to_delete = (
        HpcUser,
        HpcGroup,
        HpcProject,
        HpcGroupCreateRequest,
        HpcGroupChangeRequest,
        HpcGroupDeleteRequest,
        HpcProjectCreateRequest,
        HpcProjectChangeRequest,
        HpcProjectDeleteRequest,
        HpcUserCreateRequest,
        HpcUserChangeRequest,
        HpcUserDeleteRequest,
        HpcProjectInvitation,
        HpcGroupInvitation,
    )

    for model in hpc_object_to_delete:
        model.objects.all().delete()

    users_consented = [u.username for u in User.objects.filter(consented_to_terms=True)]
    User.objects.all().exclude(is_hpcadmin=True).exclude(is_superuser=True).exclude(
        is_staff=True
    ).delete()

    for model in hpc_object_to_delete:
        if not model.objects.count() == 0:
            return None
    else:
        return users_consented
