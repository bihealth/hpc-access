"""Create a new token for a worker user (create worker if necessary)."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from knox.models import AuthToken

User = get_user_model()


class Command(BaseCommand):
    help = "Create new (superuser) worker if necessary."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="hpc-worker", type=str)

    def handle(self, *args, **options):
        user = User.objects.get(username=options["username"])
        _, token_str = AuthToken.objects.create(user=user, expiry=None)
        self.stderr.write("Token created")
        self.stdout.write(token_str)
