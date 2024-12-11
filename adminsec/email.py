"""Email creation and sending"""

import logging
import re

from django.conf import settings
from django.contrib import auth
from django.core.mail import EmailMessage, EmailMultiAlternatives

from adminsec.constants import TIER_USER_HOME
from usersec.models import (
    INVITATION_STATUS_ACCEPTED,
    HpcGroupInvitation,
    HpcProject,
    HpcProjectInvitation,
    HpcQuotaStatus,
    HpcUser,
)

logger = logging.getLogger(__name__)
User = auth.get_user_model()


# Settings
DEBUG = settings.DEBUG
EMAIL_SENDER = settings.EMAIL_SENDER

# Local constants
EMAIL_RE = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

EMAIL_DOMAIN_TO_INSTITUTE_MAPPING = {}

if settings.ENABLE_LDAP:
    for domain in settings.INSTITUTE_EMAIL_DOMAINS.split(","):
        EMAIL_DOMAIN_TO_INSTITUTE_MAPPING[domain] = settings.AUTH_LDAP_DOMAIN_PRINTABLE

if settings.ENABLE_LDAP_SECONDARY:
    for domain in settings.INSTITUTE2_EMAIL_DOMAINS.split(","):
        EMAIL_DOMAIN_TO_INSTITUTE_MAPPING[domain] = settings.AUTH_LDAP2_DOMAIN_PRINTABLE


# ------------------------------------------------------------------------------
# Generic email text blocks
# ------------------------------------------------------------------------------

# General variables
# ------------------------------------------------------------------------------

#: Placeholder for undefined variables
UNDEFINED_VARIABLE = "<undefined>"

#: Enum for groups
HPC_OBJECT_GROUP = "group"

#: Enum for projects
HPC_OBJECT_PROJECT = "project"

#: Enum for users
HPC_OBJECT_USER = "user"

# Subject prefix & Header & footer
# ------------------------------------------------------------------------------

#: Prefix for subject lines
SUBJECT_PREFIX = "[BIH HPC Cluster] "

#: Greeting for user emails
USER_GREETING = "Dear {user},"

#: Greeting for admin emails
ADMIN_GREETING = "Dear admins,"

#: Greeting for emails with unknown recipient
NEUTRAL_GREETING = "Hello"

#: Link to the manual PIs & delegates section
MANUAL_LINK_PIS = "https://hpc-access.readthedocs.io/en/latest/usersec_pis.html"

#: Link to HPC Access
HPC_ACCESS_LINK = "https://hpc-access.cubi.bihealth.org"

#: Email footer
FOOTER = """
Best regards,
The BIH HPC Team

(This email has been automatically generated.)
""".lstrip()

FOOTER_HTML = """
<p>
Best regards,<br />
The BIH HPC Team
</p>

<p><em>(This email has been automatically generated.)</em></p>
""".lstrip()

# Admin email text blocks
# ------------------------------------------------------------------------------

#: Notification text for admins upon new request or request change
SUBJECT_ADMIN_REQUEST = SUBJECT_PREFIX + "Request submitted - {request_type}"
NOTIFICATION_ADMIN_REQUEST = """
{greeting}

a {request_type} request has been submitted by {username}. Please visit the
following link to review the request:

{hpc_access_link}

{footer}
""".lstrip()

# Manager texts (either PI or delegate, if available)
# ------------------------------------------------------------------------------

#: Notification text for visitors requesting a group.
SUBJECT_MANAGER_GROUP_REQUEST = SUBJECT_PREFIX + "Your group request"
SUBJECT_MANAGER_PROJECT_REQUEST = SUBJECT_PREFIX + "Your project request for {name}"
NOTIFICATION_MANAGER_REQUEST = """
{greeting}

you have successfully requested a {project_or_group} on the BIH HPC cluster. It
is now pending approval by the HPC administrators. You can check the status of
your request by visiting the following link:

{hpc_access_link}

{footer}
""".lstrip()

#: Notification text for managers upon group creation
SUBJECT_MANAGER_GROUP_CREATED = SUBJECT_PREFIX + "Your group {group} has been created"
NOTIFICATION_MANAGER_GROUP_CREATED = """
{greeting}

your group request has been approved and the group has been created.

You can now add members to your group, name a delegate or create projects. Find
more details in the manual:

{manual_link}

Your group folder is located at

{group_folder}

{footer}
""".lstrip()

#: Notification text for managers upon group creation
SUBJECT_MANAGER_PROJECT_CREATED = SUBJECT_PREFIX + "Your project {project} has been created"
NOTIFICATION_MANAGER_PROJECT_CREATED = """
{greeting}

your project request has been approved and the project has been created.

You can now add members to your project from different other work group and
also name a delegate. Find more details in the manual:

{manual_link}

Your project folder is located at

{project_folder}

{footer}
""".lstrip()

#: Notification text for managers upon group invitation acceptance
SUBJECT_MANAGER_USER_DECIDED_INVITATION = (
    SUBJECT_PREFIX + "User {decision} {project_or_group} invitation"
)
NOTIFICATION_MANAGER_USER_DECIDED_INVITATION = """
{greeting}

the user {username} {decision} your invitation to join {project_or_group} "{identifier}".
{account_created}
{footer}
""".lstrip()

#: Notification text for managers upon group invitation acceptance
NOTIFICATION_PART_USER_ACCOUNT_CREATED = """
The user account has been created and the user was added to the group.

""".lstrip()

#: Notification text for managers for revising a request
SUBJECT_MANAGER_REVISE_REQUEST = SUBJECT_PREFIX + "Your {request_type} request needs revision"
NOTIFICATION_MANAGER_REVISE_REQUEST = """
{greeting}

there is an update on your {request_type} request.

It hasn't been decided yet because more information is required. Please visit
the link below to revise your request:

{hpc_access_link}

{footer}
""".lstrip()

#: Notification text for managers for a declined request
SUBJECT_MANAGER_REQUEST_DENIED = SUBJECT_PREFIX + "Your {request_type} request has been declined"
NOTIFICATION_MANAGER_REQUEST_DENIED = """
{greeting}

there is an update on your {request_type} request. Unfortunately, it has been
declined. Please find more information by following the link below:

{hpc_access_link}

{footer}
""".lstrip()

#: Notification text for managers for a request approval
SUBJECT_MANAGER_REQUEST_APPROVED = SUBJECT_PREFIX + "Your {request_type} request has been approved"
NOTIFICATION_MANAGER_REQUEST_APPROVED = """
{greeting}

your {request_type} request has been approved. Please see the active changes
by following the link below:

{hpc_access_link}

{footer}
""".lstrip()

# User email text blocks
# ------------------------------------------------------------------------------

#: Invitation text for new users
SUBJECT_USER_GROUP_INVITATION = SUBJECT_PREFIX + "You've been invited to join group '{identifier}'"
NOTIFICATION_USER_GROUP_INVITATION = """
{greeting}

You've been invited by {inviter} to become member of group {identifier} with
your username {username} on the BIH HPC cluster. Head over to

{invitation_link}

and log in with your {institute} credentials. A page with a disclaimer will be shown.
Please read the text carefully. You can then accept or decline the invitation.

{footer}
""".lstrip()

#: Text for project invitations
SUBJECT_USER_PROJECT_INVITATION = (
    SUBJECT_PREFIX + "You've been invited to join project '{identifier}'"
)
NOTIFICATION_USER_PROJECT_INVITATION = """
{greeting}

You've been invited by {inviter} to become member of project {identifier} on
the BIH HPC cluster. Head over to

  {invitation_link}

and accept or deny the invitation.

{footer}
""".lstrip()

#: Welcome text for new users
SUBJECT_USER_WELCOME_MAIL = SUBJECT_PREFIX + "Welcome to the BIH HPC cluster"
NOTIFICATION_USER_WELCOME_MAIL = """
{greeting}

You have accepted the invitation to join the BIH HPC cluster. A cluster account
has been created for you. You can get more information about your cluster account
visiting

https://hpc-access.cubi.bihealth.org/

In this email you will learn how to set up your access to the BIH HPC cluster.

Anything you need to know about the cluster is documented in the manual and
this email will point you to the most important articles to get you going. The
manual also should be the first place to look at if you have further questions
about the usage of the cluster:

https://hpc-docs.cubi.bihealth.org/

## Step 1 - Generate and submit an SSH key

To access the cluster, you have to generate an SSH key. The SSH key is your
cluster access and should be protected by a password. Follow the instructions
in the manual:

https://hpc-docs.cubi.bihealth.org/connecting/generate-key/linux/
https://hpc-docs.cubi.bihealth.org/connecting/generate-key/windows/

Once you have created the SSH key, the next step depends on whether you are MDC
or Charité user:

https://hpc-docs.cubi.bihealth.org/connecting/submit-key/mdc/
https://hpc-docs.cubi.bihealth.org/connecting/submit-key/charite/

## Step 2 - Login

Please follow these instructions to proceed to the login:

https://hpc-docs.cubi.bihealth.org/connecting/ssh-basics/#connecting

Your username is:

  {username}

Depending on your operating system you can configure your SSH client further:

https://hpc-docs.cubi.bihealth.org/connecting/advanced-ssh/linux/
https://hpc-docs.cubi.bihealth.org/connecting/advanced-ssh/windows/

Your group's main shared folder can be found here:

  {group_folder}

## Problem Solving

If you are running into problems during the login process, please read our short
troubleshooting section regarding common problems:

https://hpc-docs.cubi.bihealth.org/connecting/connection-problems/

If you have general questions about HPC usage, please head to our community forum
to receive help from fellow HPC users:

https://hpc-talk.cubi.bihealth.org

{footer}
""".lstrip()

#: Notification for a quota report of an HPC object
SUBJECT_QUOTA_USER = SUBJECT_PREFIX + "Quota warning"
SUBJECT_QUOTA_GROUP_PROJECT = SUBJECT_PREFIX + "Quota warning for {entity} {name}"
FRAGMENT_QUOTA_USER = """
your home folder storage quota is approaching or has reached its limit.
Please consider cleaning up your files to avoid running into issues.
""".lstrip()
FRAGMENT_QUOTA_GROUP_PROJECT = """
one or more of your {entity} storage quotas are approaching or have reached their
limits. Please consider cleaning up your files to avoid running into issues.
""".lstrip()
NOTIFICATION_QUOTA_PLAIN = """
{greeting}

{fragment}

{table}

For more information and cleanup tips, please follow this link:
https://hpc-docs.cubi.bihealth.org/help/faq/#help-im-getting-a-quota-warning-email

{footer}
""".lstrip()
NOTIFICATION_QUOTA_HTML = """
<html>
<body>
<p>{greeting}</p>
<p>
{fragment}
</p>

<table>
{table}
</table>

<p>
For more information and cleanup tips,
<a href="https://hpc-docs.cubi.bihealth.org/help/faq/#help-im-getting-a-quota-warning-email">
please consult our documentation.
</a>
</p>

{footer}
</body>
</html>
""".lstrip()


#: Notification for a pending consent
SUBJECT_CONSENT = SUBJECT_PREFIX + "Consent required for BIH HPC cluster"
NOTIFICATION_CONSENT = """
{greeting}

there have been changes in the terms and conditions for using the BIH HPC cluster. Please visit
the following link to review them:

{hpc_access_link}

Agreeing to the updated terms and conditions is a requirement for the continued use of BIH HPC.

{footer}
""".lstrip()


# ------------------------------------------------------------------------------
# Logic
# ------------------------------------------------------------------------------


def send_mail(subject, message, recipient_list, alternative=None, dry_run=False):
    """
    Wrapper for send_mail() with logging and error messaging.

    :param subject: Message subject (string)
    :param message: Message body (string)
    :param recipient_list: Recipients of email (list)
    :param request: Request object
    :param reply_to: List of emails for the "reply-to" header (optional)
    :return: Amount of sent email (int)
    """

    if not recipient_list:
        logger.warning("No recipients given, aborting sending email")
        return 0

    messenger = EmailMultiAlternatives if alternative else EmailMessage

    try:
        m = messenger(
            subject=subject,
            body=message,
            from_email=EMAIL_SENDER,
            to=recipient_list,
        )
        if alternative:
            m.attach_alternative(alternative, "text/html")
        if dry_run:
            # Write email message to a file instead of sending it
            return f"""
Subject: {subject}
To: {','.join(recipient_list)}

{message}
""".lstrip()
        else:
            ret = m.send(fail_silently=False)
        logger.debug("Notification email sent")
        return ret

    except Exception as ex:
        error_msg = "Error sending email: {}".format(str(ex))
        logger.error(error_msg)
        if DEBUG:
            raise ex
        return 0


# ------------------------------------------------------------------------------
# Admin email notifications
# ------------------------------------------------------------------------------


def send_notification_admin_request(request):
    from adminsec.views import get_admin_emails

    subject = SUBJECT_ADMIN_REQUEST.format(request_type=request.get_request_type())
    message = NOTIFICATION_ADMIN_REQUEST.format(
        greeting=ADMIN_GREETING,
        username=request.requester.name,
        hpc_access_link=HPC_ACCESS_LINK + request.get_detail_path(admin=True),
        request_type=request.get_request_type(),
        footer=FOOTER,
    )
    return send_mail(subject, message, get_admin_emails())


# ------------------------------------------------------------------------------
# Manager email notifications
# ------------------------------------------------------------------------------


def send_notification_manager_group_request(request):
    subject = SUBJECT_MANAGER_GROUP_REQUEST.format(project_or_group=HPC_OBJECT_GROUP)
    message = NOTIFICATION_MANAGER_REQUEST.format(
        greeting=USER_GREETING.format(user=request.requester.name),
        project_or_group=HPC_OBJECT_GROUP,
        hpc_access_link=HPC_ACCESS_LINK + request.get_detail_path(),
        footer=FOOTER,
    )
    return send_mail(subject, message, [request.requester.email])


def send_notification_manager_group_created(request, group):
    subject = SUBJECT_MANAGER_GROUP_CREATED.format(group=group.name)
    message = NOTIFICATION_MANAGER_GROUP_CREATED.format(
        greeting=USER_GREETING.format(user=request.requester.name),
        manual_link=MANUAL_LINK_PIS,
        group_folder=group.folders.get("tier1_work"),
        footer=FOOTER,
    )
    return send_mail(subject, message, [request.requester.email])


def send_notification_manager_project_request(request):
    subject = SUBJECT_MANAGER_PROJECT_REQUEST.format(
        project_or_group=HPC_OBJECT_PROJECT, name=request.name
    )
    message = NOTIFICATION_MANAGER_REQUEST.format(
        greeting=USER_GREETING.format(user=request.requester.name),
        project_or_group=HPC_OBJECT_PROJECT,
        hpc_access_link=HPC_ACCESS_LINK + request.get_detail_path(),
        footer=FOOTER,
    )
    return send_mail(subject, message, [request.requester.email])


def send_notification_manager_project_created(request, project):
    subject = SUBJECT_MANAGER_PROJECT_CREATED.format(project=project.name)
    message = NOTIFICATION_MANAGER_PROJECT_CREATED.format(
        greeting=USER_GREETING.format(user=request.requester.name),
        manual_link=MANUAL_LINK_PIS,
        project_folder=project.folders.get("tier1_work"),
        footer=FOOTER,
    )
    return send_mail(subject, message, [request.requester.email])


def send_notification_manager_request_approved(request):
    subject = SUBJECT_MANAGER_REQUEST_APPROVED.format(
        request_type=request.get_request_type(),
    )
    message = NOTIFICATION_MANAGER_REQUEST_APPROVED.format(
        greeting=USER_GREETING.format(user=request.requester.name),
        request_type=request.get_request_type(),
        hpc_access_link=HPC_ACCESS_LINK + request.get_detail_path(),
        footer=FOOTER,
    )
    return send_mail(subject, message, [request.requester.email])


def send_notification_manager_user_decided_invitation(invitation):
    identifier = UNDEFINED_VARIABLE
    username = UNDEFINED_VARIABLE
    project_or_group = UNDEFINED_VARIABLE
    account_created = ""
    email = ""
    requester_name = UNDEFINED_VARIABLE

    if isinstance(invitation, HpcGroupInvitation):
        identifier = invitation.hpcusercreaterequest.group.name
        username = invitation.username
        project_or_group = HPC_OBJECT_GROUP
        email = invitation.hpcusercreaterequest.requester.email
        requester_name = invitation.hpcusercreaterequest.requester.name

        if invitation.status == INVITATION_STATUS_ACCEPTED:
            account_created = NOTIFICATION_PART_USER_ACCOUNT_CREATED

    elif isinstance(invitation, HpcProjectInvitation):
        identifier = invitation.project.name
        username = invitation.user.user.name
        project_or_group = HPC_OBJECT_PROJECT

        if invitation.hpcprojectcreaterequest:
            email = invitation.hpcprojectcreaterequest.requester.email
            requester_name = invitation.hpcprojectcreaterequest.requester.name

        elif invitation.hpcprojectcreaterequest:
            email = invitation.hpcprojectcreaterequest.requester.email
            requester_name = invitation.hpcprojectcreaterequest.requester.name

    subject = SUBJECT_MANAGER_USER_DECIDED_INVITATION.format(
        decision=invitation.status, project_or_group=project_or_group
    )
    message = NOTIFICATION_MANAGER_USER_DECIDED_INVITATION.format(
        greeting=USER_GREETING.format(user=requester_name),
        username=username,
        decision=invitation.status,
        project_or_group=project_or_group,
        identifier=identifier,
        account_created=account_created,
        footer=FOOTER,
    )
    return send_mail(subject, message, [email])


def send_notification_manager_revision_required(request):
    subject = SUBJECT_MANAGER_REVISE_REQUEST.format(request_type=request.get_request_type())
    message = NOTIFICATION_MANAGER_REVISE_REQUEST.format(
        greeting=USER_GREETING.format(user=request.requester.name),
        request_type=request.get_request_type(),
        hpc_access_link=HPC_ACCESS_LINK + request.get_detail_path(),
        footer=FOOTER,
    )
    return send_mail(subject, message, [request.requester.email])


def send_notification_manager_request_denied(request):
    subject = SUBJECT_MANAGER_REQUEST_DENIED.format(request_type=request.get_request_type())
    message = NOTIFICATION_MANAGER_REQUEST_DENIED.format(
        greeting=USER_GREETING.format(user=request.requester.name),
        request_type=request.get_request_type(),
        hpc_access_link=HPC_ACCESS_LINK + request.get_detail_path(),
        footer=FOOTER,
    )
    return send_mail(subject, message, [request.requester.email])


def send_notification_storage_quota(hpc_obj, report, dry_run=False):
    if isinstance(hpc_obj, HpcUser):
        email = hpc_obj.get_user_email()
        name = hpc_obj.user.name
        if not email:
            logger.warning(f"User {name} has no valid email address: {hpc_obj.user.email}")
            return 0
        greeting = USER_GREETING.format(user=name)
        subject = SUBJECT_QUOTA_USER
        fragment = FRAGMENT_QUOTA_USER
        emails = [email]
        unit = "GB"
        folders = {TIER_USER_HOME: hpc_obj.home_directory}
    else:
        contacts = hpc_obj.get_manager_contact(slim=True)
        greeting = USER_GREETING.format(user=", ".join([c["name"] for c in contacts.values()]))
        emails = [c["email"] for c in contacts.values()]
        entity = "project" if isinstance(hpc_obj, HpcProject) else "group"
        name = hpc_obj.name if entity == "project" else f"AG {hpc_obj.name.capitalize()}"
        subject = SUBJECT_QUOTA_GROUP_PROJECT.format(entity=entity, name=name)
        fragment = FRAGMENT_QUOTA_GROUP_PROJECT.format(entity=entity)
        unit = "TB"
        folders = hpc_obj.folders

    table_text = f"folder | quota [{unit}] | used [{unit}] | % | warning \n"
    table_html = f"<tr><th>folder</th><th>quota [{unit}]</th><th>used [{unit}]</th><th></th></tr>\n"
    for tier, status in report["status"].items():
        data = {
            "folder": folders.get(tier),
            "requested": hpc_obj.resources_requested.get(tier),
            "used": hpc_obj.resources_used.get(tier),
            "percent": int(report["percentage"].get(tier)),
        }
        warning = ""
        style = ""
        if status == HpcQuotaStatus.RED:
            warning = "LIMIT REACHED"
            style = "background-color: red; color: white"
        elif status == HpcQuotaStatus.YELLOW:
            warning = "APPROACHING LIMIT"
            style = "background-color: yellow"
        table_text += "{folder} | {requested:.1f} | {used:.1f} | {percent}% | {warning}\n".format(
            **data, warning=warning
        )
        table_html += (
            "<tr style='{style}'>"
            "<td>{folder}</td>"
            "<td style='text-align: right'>{requested:.1f}</td>"
            "<td style='text-align: right'>{used:.1f}</td>"
            "<td style='text-align: right'>{percent}%</td>"
            "</tr>\n"
        ).format(**data, style=style)

    message_html = NOTIFICATION_QUOTA_HTML.format(
        greeting=greeting,
        name=name,
        fragment=fragment,
        table=table_html,
        footer=FOOTER_HTML,
    )
    message_text = NOTIFICATION_QUOTA_PLAIN.format(
        greeting=greeting,
        name=name,
        fragment=fragment,
        table=table_text,
        footer=FOOTER,
    )
    logger.info(f"Sending quota email: {emails}, '{subject}'")
    return send_mail(subject, message_text, emails, alternative=message_html, dry_run=dry_run)


# ------------------------------------------------------------------------------
# User email notifications
# ------------------------------------------------------------------------------


def send_notification_user_invitation(invitation):
    subject = UNDEFINED_VARIABLE
    email = None
    message = UNDEFINED_VARIABLE

    if isinstance(invitation, HpcGroupInvitation):
        email = invitation.hpcusercreaterequest.email
        subject = SUBJECT_USER_GROUP_INVITATION.format(
            identifier=invitation.hpcusercreaterequest.group.name
        )
        message = NOTIFICATION_USER_GROUP_INVITATION.format(
            greeting=NEUTRAL_GREETING,
            inviter=invitation.hpcusercreaterequest.requester.name,
            identifier=invitation.hpcusercreaterequest.group.name,
            username=invitation.username,
            invitation_link=HPC_ACCESS_LINK,
            institute=EMAIL_DOMAIN_TO_INSTITUTE_MAPPING.get(
                email.split("@")[1], UNDEFINED_VARIABLE
            ),
            footer=FOOTER,
        )

    elif isinstance(invitation, HpcProjectInvitation):
        email = invitation.user.user.email
        subject = SUBJECT_USER_PROJECT_INVITATION.format(identifier=invitation.project.name)
        inviter = UNDEFINED_VARIABLE

        if invitation.hpcprojectcreaterequest:
            inviter = invitation.hpcprojectcreaterequest.requester.name

        elif invitation.hpcprojectchangerequest:
            inviter = invitation.hpcprojectchangerequest.requester.name

        message = NOTIFICATION_USER_PROJECT_INVITATION.format(
            greeting=USER_GREETING.format(user=invitation.user.user.name),
            inviter=inviter,
            identifier=invitation.project.name,
            invitation_link=HPC_ACCESS_LINK,
            footer=FOOTER,
        )

    if email:
        return send_mail(subject, message, [email])

    else:
        raise Exception("No email given to send user invitation")


def send_notification_user_welcome_mail(user):
    subject = SUBJECT_USER_WELCOME_MAIL
    message = NOTIFICATION_USER_WELCOME_MAIL.format(
        greeting=USER_GREETING.format(user=user.user.name),
        username=user.username,
        group_folder=user.primary_group.folders.get("tier1_work"),
        footer=FOOTER,
    )
    return send_mail(subject, message, [user.user.email])


def send_notification_user_consent(user):
    subject = SUBJECT_CONSENT
    message = NOTIFICATION_CONSENT.format(
        greeting=USER_GREETING.format(user=user.name),
        hpc_access_link=HPC_ACCESS_LINK,
        footer=FOOTER,
    )
    return send_mail(subject, message, [user.email])
