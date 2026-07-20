"""Sync user information with upstream LDAP(s)."""

from django.core.management.base import BaseCommand

from adminsec.tasks import _send_quota_email
from usersec.models import HpcQuotaStatus

EMAIL_FILE = "quota_emails.txt"


class Command(BaseCommand):
    help = "Send quota emails to users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-dry-run",
            action="store_true",
            help="Disable dry run mode and send actual emails.",
        )
        parser.add_argument(
            "level",
            choices=["yellow", "red"],
            help="Specify the quota alert level for the emails. Accepted values are YELLOW or RED.",
        )

    def handle(self, *args, **options):
        self.stderr.write("Sending quota emails...")

        level_map = {
            "yellow": HpcQuotaStatus.YELLOW,
            "red": HpcQuotaStatus.RED,
        }

        response = [
            e
            for e in _send_quota_email(
                level_map[options["level"]], dry_run=not options["no_dry_run"]
            )
            if isinstance(e, str)
        ]

        if options["no_dry_run"]:
            self.stderr.write("Quota emails sent.")

        else:
            self.stderr.write(
                f"Dry run mode enabled. {len(response)} email(s) would have been sent."
            )
            self.stderr.write(f"Writing emails to file {EMAIL_FILE}")

            with open(EMAIL_FILE, "w") as file:
                file.write(f"\n{'-' * 80}\n".join(response))
