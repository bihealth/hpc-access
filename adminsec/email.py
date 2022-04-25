"""Email creation and sending"""

import logging
import re

from django.conf import settings
from django.contrib import auth, messages
from django.core.mail import EmailMessage
from django.urls import reverse

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


MESSAGE_USER_INVITE = r"""
You've been invited by

  {inviter}

to become member of

  {ag}

on the BIH cluster. The following link will require you to login with your
{institute} credentials. This will complete the registration.

{invitation_link}

Cheers,
  Gatekeeper

This email has been automatically generated.
""".lstrip()


MESSAGE_USER_ADDED_TO_PROJECT_NOTIFICATION = r"""
Hello,

you have been added to the project {project_name}.

Its location on the cluster: {project_folder}

Leader of the project is {project_owner_name}.

Cheers,
  Gatekeeper

This email has been automatically generated.
""".lstrip()


MESSAGE_PROJECT_CREATED_NOTIFICATION = r"""
Dear {full_name},

the project {project_name} has been approved and created.

Cheers,
  Gatekeeper

This email has been automatically generated.
""".lstrip()


# TODO add hpc talk
WELCOME_MAIL = r"""
Hello and welcome {full_name}!

In this email you will learn how to set up your access to the BIH cluster.

Anything you need to know about the cluster is documented in the manual, and
this email will point you to the most important articles to get you going. The
manual also should be the first place to look at if you have further questions
about the usage of the cluster:

http://hpc-docs.cubi.bihealth.org/

<h6>Step 1 - Generate and submit an SSH key</h6>

To access the cluster, you have to generate an SSH key. The SSH key is your
cluster access and should be protected by a password. Follow the instructions
in the manual:

https://bihealth.github.io/bih-cluster/connecting/generate-key/linux/
https://bihealth.github.io/bih-cluster/connecting/generate-key/windows/

Once you have created the SSH key, the next step depends on whether you are MDC
or Charité user:

https://bihealth.github.io/bih-cluster/connecting/submit-key/mdc/
https://bihealth.github.io/bih-cluster/connecting/submit-key/charite/

<h6>Step 2 - Login</h6>

Please follow the instructions to proceed to the login. Your username is
constructed from your MDC/Charité username with an appendix distinguishing the
two institutes as described here:

https://bihealth.github.io/bih-cluster/connecting/configure-ssh/prerequisites/

Depending on your operating system, please follow the instructions on how to
configure your SSH client:

https://bihealth.github.io/bih-cluster/connecting/configure-ssh/linux/
https://bihealth.github.io/bih-cluster/connecting/configure-ssh/windows/

<h6>Problem Solving</h6>

If you are running into problems during the login process, we provide you with
a mini FAQ regarding common problems:

https://bihealth.github.io/bih-cluster/connecting/configure-ssh/connection-problems/

If you have general questions about the usage, please head to our portal to
post your question and receive help from the community:

https://hpc-talk.cubi.bihealth.org

Cheers,
  Gatekeeper

<em>This email has been automatically generated.</em>
""".lstrip()


def send_user_invite(recipient_list, inviter, request=None):
    institute = "???"
    invitation_link = "???"

    if len(recipient_list) > 1:
        institute = "institutes"

    elif len(recipient_list) == 1:
        user_domain = recipient_list[0].split("@")

        if len(user_domain) == 2:
            institute = EMAIL_DOMAIN_TO_INSTITUTE_MAPPING.get(user_domain[1], "???")

    else:
        return 0

    if request:
        invitation_link = request.build_absolute_uri(reverse("home"))

    subject = "Invitation for a BIH Cluster account"
    message = MESSAGE_USER_INVITE.format(
        site_title=settings.SITE_TITLE,
        inviter=inviter.user.name,
        ag=inviter.primary_group.name,
        institute=institute,
        invitation_link=invitation_link,
    )
    return send_mail(subject, message, recipient_list, request)


def send_user_added_to_project_notification(project, request=None):
    subject = "Added to project on BIH cluster"
    recipient_list = [m.user.email for m in project.members.exclude(user__isnull=True)]
    message = MESSAGE_USER_ADDED_TO_PROJECT_NOTIFICATION.format(
        project_name=project.name,
        project_folder=project.folder,
        project_owner_name=project.group.owner.user.name,
    )
    return send_mail(subject, message, recipient_list, request)


def send_project_created_notification(project, request=None):
    subject = "Project approved and created"
    recipient_list = [project.group.owner.user.email]
    message = MESSAGE_PROJECT_CREATED_NOTIFICATION.format(
        full_name=project.group.owner.user.name,
        project_name=project.name,
    )
    return send_mail(subject, message, recipient_list, request)


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

        success_msg = "Email sent to {}".format(", ".join(recipient_list))
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
