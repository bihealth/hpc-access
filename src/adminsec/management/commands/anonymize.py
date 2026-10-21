"""Command for permanently removing personal data assiciated with a user."""

from django.contrib import auth
from django.core.management.base import BaseCommand

User = auth.get_user_model()


def anonymize_user(user: User):
    user.is_active = False
    user.consented_to_terms = False
    user.first_name = ""
    user.last_name = ""
    user.display_name = ""
    user.name = ""
    user.email = ""
    user.phone = ""
    user.last_login = None
    user.save()


class Command(BaseCommand):
    help = "Anonymize a user to comply with GDPR data deletion request."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument(
            "-i",
            "--interactive",
            action="store_true",
            help="Ask for confirmation before making changes",
        )

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            self.stderr.write(f'User "{options["username"]}" does not exist.')
            return

        if options["interactive"]:
            self.stderr.write(
                "Warning: you are about to permanently deactivate and remove all data "
                f'for user "{options["username"]}". This action cannot be undone. '
                # 'Unless you have a backup of the database...'
            )
            ans = input("Do you want to proceed? [Y/n]: ")
            if ans and not ans.lower().startswith("y"):
                self.stdout.write("Operation aborted, bye for now.")
                return

        anonymize_user(user)
