"""Create a new (superuser) worker user."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from knox.models import AuthToken

User = get_user_model()


class Command(BaseCommand):
    help = "Create new (superuser) worker if necessary."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="hpc-worker", type=str)

    def handle(self, *args, **options):
        users = User.objects.filter(username=options["username"])
        if users:
            self.stderr.write("User already exists... will only look for token.")
            user = users[0]
        else:
            user = User.objects.create(
                username=options["username"], is_staff=True, is_superuser=True
            )

        tokens = AuthToken.objects.filter(user=user)
        if tokens:
            self.stderr.write("Token already exists... skipping")
        else:
            _, token_str = AuthToken.objects.create(user=user, expiry=None)
            self.stderr.write("Token created")
            self.stdout.write(token_str)
