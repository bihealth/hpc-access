# Create your tasks here
import logging
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


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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

            if user.hpcuser_user.exists():
                hpcuser = user.hpcuser_user.first()
                if disabled:
                    hpcuser.status = "EXPIRED"
                    hpcuser.login_shell = "/usr/sbin/nologin"
                else:
                    hpcuser.status = "ACTIVE"
                    hpcuser.login_shell = "/bin/bash"

                if write:
                    hpcuser.save()

            if write:
                user.save()

        except Exception as e:
            exception_count[str(e)] += 1
            continue

    return exception_count


def _generate_quota_reports():
    logger.info("Generating quota reports ...")
    return {
        "users": {o: o.generate_quota_report() for o in HpcUser.objects.all()},
        "projects": {o: o.generate_quota_report() for o in HpcProject.objects.all()},
        "groups": {o: o.generate_quota_report() for o in HpcGroup.objects.all()},
    }


def _send_quota_email(status, dry_run=False):
    if not settings.SEND_QUOTA_EMAILS and not dry_run:
        logger.info("Quota emails are disabled ... aborting.")
        return

    reports = _generate_quota_reports()
    response = []

    for data in reports.values():
        for hpc_obj, report in data.items():
            if any([s > status for s in report["status"].values()]):
                # Skip if the object is already in a worse state
                logger.info(f"Skipping {hpc_obj} as it is already in a worse state")
                continue

            if any([s == status for s in report["status"].values()]):
                response.append(send_notification_storage_quota(hpc_obj, report, dry_run=dry_run))

    return response


@app.task(bind=True)
def send_quota_email_yellow(_self):
    logger.info("Sending quota email for status YELLOW")
    _send_quota_email(HpcQuotaStatus.YELLOW)


@app.task(bind=True)
def send_quota_email_red(_self):
    logger.info("Sending quota email for status RED")
    _send_quota_email(HpcQuotaStatus.RED)


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
        logger.info(f"Deleting {model.objects.count()} {model.__name__} objects")
        model.objects.all().delete()

    users_consented = [u.username for u in User.objects.filter(consented_to_terms=True)]
    User.objects.all().exclude(is_hpcadmin=True).exclude(is_superuser=True).exclude(
        is_staff=True
    ).delete()

    for model in hpc_object_to_delete:
        if not model.objects.count() == 0:
            logger.info("Failed to clean database of HPC objects ... aborting.")
            return None
    else:
        return users_consented
