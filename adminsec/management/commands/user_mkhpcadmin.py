"""Create a new hpcadmin user."""

import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Create new hpcadmin if necessary."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        users = User.objects.filter(username=options["username"])

        if users:
            self.stderr.write("User already exists.")
            return

        password = getpass.getpass()
        password2 = getpass.getpass("Password (again): ")

        if password != password2:
            self.stderr.write("Error: Your passwords didn't match.")
            # Don't validate passwords that don't match.
            return

        if password.strip() == "":
            self.stderr.write("Error: Blank passwords aren't allowed.")
            # Don't validate blank passwords.
            return

        try:
            validate_password(password2)

        except exceptions.ValidationError as err:
            self.stderr.write("\n".join(err.messages))
            response = input("Bypass password validation and create user anyway? [y/N]: ")
            if response.lower() != "y":
                return

        user = User.objects.create(username=options["username"], is_hpcadmin=True)
        user.set_password(password)
        user.save()
        self.stderr.write(f"User '{options['username']}' created")
