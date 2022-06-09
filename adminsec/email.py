"""Email creation and sending"""

import logging
import re

from django.conf import settings
from django.contrib import auth, messages
from django.core.mail import EmailMessage
from django.urls import reverse

from usersec.models import (
    HpcGroupChangeRequest,
    HpcProjectChangeRequest,
    HpcUserChangeRequest,
    HpcGroupCreateRequest,
    HpcProjectCreateRequest,
    HpcUserCreateRequest,
    HpcGroupInvitation,
    HpcProjectInvitation,
    HpcGroup,
    HpcProject,
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
# Generic Elements
# ------------------------------------------------------------------------------

NOTIFICATION_GROUP_INVITATION = r"""
{greeting}

You've been invited by

  {inviter}

to become member of group

  {identifier}

on the BIH cluster. The following link will require you to login with your
{institute} credentials and accept or decline the invitation.

  {invitation_link}

Cheers,
  Gatekeeper

{disclaimer}
""".lstrip()


NOTIFICATION_PROJECT_INVITATION = r"""
{greeting}

You've been invited by

  {inviter}

to become member of project

  {identifier}

on the BIH cluster. Please login to the portal and accept or deny the invitation.

Cheers,
  Gatekeeper

{disclaimer}
""".lstrip()


WELCOME_MAIL = r"""
{greeting}

In this email you will learn how to set up your access to the BIH cluster.

Anything you need to know about the cluster is documented in the manual, and
this email will point you to the most important articles to get you going. The
manual also should be the first place to look at if you have further questions
about the usage of the cluster:

http://hpc-docs.cubi.bihealth.org/

## Step 1 - Generate and submit an SSH key

To access the cluster, you have to generate an SSH key. The SSH key is your
cluster access and should be protected by a password. Follow the instructions
in the manual:

https://bihealth.github.io/bih-cluster/connecting/generate-key/linux/
https://bihealth.github.io/bih-cluster/connecting/generate-key/windows/

Once you have created the SSH key, the next step depends on whether you are MDC
or Charité user:

https://bihealth.github.io/bih-cluster/connecting/submit-key/mdc/
https://bihealth.github.io/bih-cluster/connecting/submit-key/charite/

## Step 2 - Login

Please follow the instructions to proceed to the login. Your username is

  {username}

Depending on your operating system, please follow the instructions on how to
configure your SSH client:

https://bihealth.github.io/bih-cluster/connecting/configure-ssh/linux/
https://bihealth.github.io/bih-cluster/connecting/configure-ssh/windows/

Please find the group folder in

  {group_folder}

## Problem Solving

If you are running into problems during the login process, we provide you with
a mini FAQ regarding common problems:

https://bihealth.github.io/bih-cluster/connecting/configure-ssh/connection-problems/

If you have general questions about the usage, please head to our portal to
post your question and receive help from the community:

https://hpc-talk.cubi.bihealth.org

Cheers,
  Gatekeeper

{disclaimer}
""".lstrip()


NOTIFICATION_USER_DECIDED_INVITATION = r"""
{greeting}

user {username} has {decision} the invitation to {project_or_group} {identifier}.

{disclaimer}
""".lstrip()


DISCLAIMER = "This email has been automatically generated."

USER_GREETING = "Dear {user}"

PROJECT_MANAGER_GREETING = "Dear project managers"

GROUP_MANAGER_GREETING = "Dear group managers"

ADMIN_GREETING = "Dear admins"

NEUTRAL_GREETING = "Hello"

NOTIFICATION_USER_REQUEST = r"""
{greeting}

the {request} "{identifier}" has been set to {status} by user {user}.

{disclaimer}
""".lstrip()


UNDEFINED_VARIABLE = "<undefined>"


HPC_OBJECT_GROUP = "group"
HPC_OBJECT_PROJECT = "project"
HPC_OBJECT_USER = "user"


MANAGER_NOTIFICATION_USER_ACCEPTED_INVITATION = r"""
{greeting}

the user {user} accepted your invitation to join {project_or_group} "{identifier}".

{disclaimer}
""".lstrip()


USER_NOTIFICATION_USER_ACCEPTED_INVITATION = r"""
{greeting}

you accepted the invitation to join {project_or_group} "{identifier}".

{disclaimer}
""".lstrip()


NOTIFICATION_OBJECT_CREATED = r"""
{greeting}

The {object} "{identifier}" has been created.
{folder_section}
{disclaimer}
""".lstrip()


NOTIFICATION_OBJECT_CREATED_FOLDER_SECTION = r"""
Its location on the cluster:

  {folder}

"""


NOTIFICATION_OBJECT_UPDATED = r"""
{greeting}

The {object} "{identifier}" has been updated.

{disclaimer}
""".lstrip()


NOTIFICATION_USER_INVITED = r"""
{greeting}

The user has been invited to join {project_or_group} "{identifier}".
The user can accept or decline your invitation.

{disclaimer}
""".lstrip()


def send_mail(subject, message, recipient_list, request=None):
    """
    Wrapper for send_mail() with logging and error messaging.

    :param subject: Message subject (string)
    :param message: Message body (string)
    :param recipient_list: Recipients of email (list)
    :param request: Request object
    :param reply_to: List of emails for the "reply-to" header (optional)
    :return: Amount of sent email (int)
    """
    try:
        m = EmailMessage(
            subject=subject,
            body=message,
            from_email=EMAIL_SENDER,
            to=recipient_list,
        )
        ret = m.send(fail_silently=False)

        success_msg = "Notification email sent"
        logger.debug(success_msg)

        if request:
            messages.success(request, success_msg)

        return ret

    except Exception as ex:
        error_msg = "Error sending email: {}".format(str(ex))
        logger.error(error_msg)

        if DEBUG:
            raise ex

        if request:
            messages.error(request, error_msg)

        return 0


def send_notification_request_status_changed(recipient_list, obj, request=None):
    name = obj.__class__.__name__
    subject = f"{name} has been set to {obj.status}"
    identifier = UNDEFINED_VARIABLE

    if isinstance(obj, HpcGroupChangeRequest):
        identifier = obj.group.name

    elif isinstance(obj, HpcProjectChangeRequest):
        identifier = obj.project.name

    elif isinstance(obj, HpcUserChangeRequest):
        identifier = obj.user.user.name

    elif isinstance(obj, HpcGroupCreateRequest):
        identifier = obj.requester.username

    elif isinstance(obj, HpcProjectCreateRequest):
        identifier = obj.name

    elif isinstance(obj, HpcUserCreateRequest):
        identifier = obj.email

    message = NOTIFICATION_USER_REQUEST.format(
        greeting=NEUTRAL_GREETING,
        request=name,
        identifier=identifier,
        status=obj.status,
        user=obj.requester.name,
        disclaimer=DISCLAIMER,
    )
    return send_mail(subject, message, recipient_list, request)


def send_notification_user_decided_invitation(invitation, request=None):
    subject = UNDEFINED_VARIABLE
    identifier = UNDEFINED_VARIABLE
    username = UNDEFINED_VARIABLE
    project_or_group = UNDEFINED_VARIABLE
    emails = []

    if isinstance(invitation, HpcGroupInvitation):
        identifier = invitation.hpcusercreaterequest.group.name
        username = invitation.username
        project_or_group = HPC_OBJECT_GROUP
        emails = invitation.hpcusercreaterequest.group.get_manager_emails()
        subject = f"User {invitation.status} group invitation"

    elif isinstance(invitation, HpcProjectInvitation):
        identifier = invitation.project.name
        username = invitation.user.user.name
        project_or_group = HPC_OBJECT_PROJECT
        emails = invitation.project.get_manager_emails()
        subject = f"User {invitation.status} project invitation"

    message = NOTIFICATION_USER_DECIDED_INVITATION.format(
        greeting=NEUTRAL_GREETING,
        username=username,
        decision=invitation.status,
        project_or_group=project_or_group,
        identifier=identifier,
        disclaimer=DISCLAIMER,
    )
    return send_mail(subject, message, emails, request)


def send_notification_user_has_invitation(invitation, request=None):
    subject = UNDEFINED_VARIABLE
    email = None
    message = UNDEFINED_VARIABLE

    if isinstance(invitation, HpcGroupInvitation):
        email = invitation.hpcusercreaterequest.email
        subject = "User accepted group invitation"
        link = ""

        if request:
            link = request.build_absolute_uri(reverse("home"))

        message = NOTIFICATION_GROUP_INVITATION.format(
            greeting=NEUTRAL_GREETING,
            inviter=invitation.hpcusercreaterequest.requester.name,
            identifier=invitation.hpcusercreaterequest.group.name,
            invitation_link=link,
            institute=EMAIL_DOMAIN_TO_INSTITUTE_MAPPING.get(
                email.split("@")[1], UNDEFINED_VARIABLE
            ),
            disclaimer=DISCLAIMER,
        )

    elif isinstance(invitation, HpcProjectInvitation):
        email = invitation.user.user.email
        subject = "User accepted project invitation"
        inviter = UNDEFINED_VARIABLE

        if invitation.hpcprojectcreaterequest:
            inviter = invitation.hpcprojectcreaterequest.requester.name

        elif invitation.hpcprojectchangerequest:
            inviter = invitation.hpcprojectchangerequest.requester.name

        message = NOTIFICATION_PROJECT_INVITATION.format(
            greeting=NEUTRAL_GREETING,
            inviter=inviter,
            identifier=invitation.project.name,
            disclaimer=DISCLAIMER,
        )

    if email:
        return send_mail(subject, message, [email], request)

    else:
        raise Exception("No email given to send user invitation")


def send_welcome_mail(user, request=None):
    subject = "Welcome to the BIH cluster"
    message = WELCOME_MAIL.format(
        greeting=USER_GREETING.format(user=user.user.name),
        username=user.username,
        group_folder=user.primary_group.folder,
        disclaimer=DISCLAIMER,
    )
    return send_mail(subject, message, [user.user.email], request)


def send_notification_object_created(recipient_list, obj, request=None):
    obj_type = UNDEFINED_VARIABLE
    identifier = UNDEFINED_VARIABLE
    folder_section = ""

    if isinstance(obj, HpcGroup):
        obj_type = HPC_OBJECT_GROUP
        identifier = obj.name
        folder_section = NOTIFICATION_OBJECT_CREATED_FOLDER_SECTION.format(folder=obj.folder)

    elif isinstance(obj, HpcProject):
        obj_type = HPC_OBJECT_PROJECT
        identifier = obj.name
        folder_section = NOTIFICATION_OBJECT_CREATED_FOLDER_SECTION.format(folder=obj.folder)

    elif isinstance(obj, HpcUser):
        obj_type = HPC_OBJECT_USER
        identifier = obj.username

    subject = "{} has been created".format(obj_type.capitalize())
    message = NOTIFICATION_OBJECT_CREATED.format(
        greeting=NEUTRAL_GREETING,
        object=obj_type,
        folder_section=folder_section,
        identifier=identifier,
        disclaimer=DISCLAIMER,
    )
    return send_mail(subject, message, recipient_list, request)


def send_notification_object_updated(recipient_list, obj, request=None):
    obj_type = UNDEFINED_VARIABLE
    identifier = UNDEFINED_VARIABLE

    if isinstance(obj, HpcGroup):
        obj_type = HPC_OBJECT_GROUP
        identifier = obj.name

    elif isinstance(obj, HpcProject):
        obj_type = HPC_OBJECT_PROJECT
        identifier = obj.name

    elif isinstance(obj, HpcUser):
        obj_type = HPC_OBJECT_USER
        identifier = obj.username

    subject = "{} has been updated".format(obj_type.capitalize())
    message = NOTIFICATION_OBJECT_UPDATED.format(
        greeting=NEUTRAL_GREETING,
        object=obj_type,
        folder=obj.folder,
        identifier=identifier,
        disclaimer=DISCLAIMER,
    )
    return send_mail(subject, message, recipient_list, request)
