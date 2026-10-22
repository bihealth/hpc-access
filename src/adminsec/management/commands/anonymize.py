"""Command for permanently removing personal data associated with a user."""

import uuid

from django.contrib import auth
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import now

from usersec.models import OBJECT_STATUS_EXPIRED, HpcUserCreateRequest, HpcUserCreateRequestEvent

User = auth.get_user_model()


def anonymize_user(user: User):
    with transaction.atomic():
        # Expire related HpcUsers
        for hpcuser in user.hpcuser_user.all():
            hpcuser.status = OBJECT_STATUS_EXPIRED
            hpcuser.login_shell = "/usr/sbin/nologin"
            hpcuser.save()
        # Remove user private data from related database objects
        # XXX: should we also clear out comment fields? How relistic
        # is it to find PII data there? And how should we look for it?
        if email := user.email:
            for req in HpcUserCreateRequest.objects.filter(email=email):
                req.email = ""
                req.soft_delete()
            for req_event in HpcUserCreateRequestEvent.objects.filter(email=email):
                req_event.email = ""
                req_event.save()
        # Clear the user object fields
        user.is_active = False
        user.consented_to_terms = False
        user.is_superuser = False
        user.is_staff = False
        user.is_hpcadmin = False
        user.first_name = ""
        user.last_name = "Anonymous"
        user.display_name = ""
        user.name = str(uuid.uuid4())
        user.email = ""
        user.phone = ""
        user.last_login = None
        user.anonymized_at = now()
        user.set_unusable_password()
        user.save()


class Command(BaseCommand):
    help = "Anonymize a user to comply with GDPR data deletion request."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_true",
            help="Do NOT prompt the user for confirmation before making changes.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as ex:
            raise CommandError(f'User "{username}" does not exist.') from ex

        if user.anonymized_at is not None:
            raise CommandError(f'User "{username}" is already anonymized.')

        if not options["noinput"]:
            self.stderr.write(
                "Warning: you are about to permanently deactivate and remove all data "
                f'for user "{username}". This action cannot be undone. '
                # Unless the LDAP server keeps records for the user
                # or you have a backup of the database
            )
            if user.hpcuser_user.exists():
                self.stderr.write(
                    "In addition, the related HpcUser object "
                    f"will be marked as {OBJECT_STATUS_EXPIRED}."
                )
            if user.email and HpcUserCreateRequest.objects.filter(email=user.email).exists():
                self.stderr.write(
                    f"{HpcUserCreateRequest.objects.filter(email=user.email).count()} "
                    "HpcUserCreateRequests for this user will be deleted."
                )
            ans = input("Do you want to proceed? [y/N]: ")
            if not ans or not ans.lower().startswith("y"):
                self.stdout.write("Operation aborted, bye for now.")
                return

        anonymize_user(user)
        self.stdout.write(f'User "{username}" has been anonymized.')
