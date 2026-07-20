"""Sync user information with upstream LDAP(s)."""

from django.core.management.base import BaseCommand

from adminsec.tasks import _sync_ldap


class Command(BaseCommand):
    help = "Sync user information with upstream LDAP(s)."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", help="Actually sync LDAP.")
        parser.add_argument("--verbose", action="store_true", help="Enable LDAP connector logging.")

    def handle(self, *args, **options):
        self.stderr.write("Syncing LDAP...")

        # Sync LDAP
        exception_count = _sync_ldap(write=options["write"], verbose=options["verbose"])

        # Print exceptions
        for key, value in exception_count.items():
            if value > 1:
                self.stderr.write(f"{key} (seen {value}x)")
            else:
                self.stderr.write(str(key))

        self.stderr.write("LDAP sync complete.")
