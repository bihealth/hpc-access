"""Tests for the ``anonymize`` management command"""

from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

User = get_user_model()


class TestAnonymizeCommand(TestCase):
    def setUp(self):
        super().setUp()
        self.user, _ = User.objects.get_or_create(
            consented_to_terms=True,
            email="maxmustermann@bih.de",
            first_name="Max",
            last_name="Mustermann",
            phone="123-456-789",
            username="user",
        )
        self.command = "anonymize"

    def test_anonymization(self):
        call_command(self.command, self.user.username)
        self.user.refresh_from_db()
        self.assertEqual(self.user.is_active, False)
        self.assertEqual(self.user.consented_to_terms, False)
        self.assertEqual(self.user.first_name, "")
        self.assertEqual(self.user.last_name, "")
        self.assertEqual(self.user.display_name, "")
        self.assertEqual(self.user.name, "")
        self.assertEqual(self.user.email, "")
        self.assertEqual(self.user.phone, "")
        self.assertEqual(self.user.last_login, None)

    def test_user_not_found(self):
        err = StringIO()
        call_command(self.command, "no such user", stderr=err)
        self.user.refresh_from_db()
        self.assertEqual(self.user.is_active, True)
        self.assertIn('User "no such user" does not exist.', err.getvalue())

    def test_interactive_mode(self):
        out = StringIO()
        with mock.patch("builtins.input", return_value="n"):
            call_command(self.command, self.user, "--interactive", stdout=out)
        self.user.refresh_from_db()
        self.assertEqual(self.user.is_active, True)
        self.assertEqual(self.user.consented_to_terms, True)
        self.assertEqual(self.user.first_name, "Max")
        self.assertEqual(self.user.last_name, "Mustermann")
        self.assertEqual(self.user.email, "maxmustermann@bih.de")
        self.assertEqual(self.user.phone, "123-456-789")
        self.assertIn("Operation aborted, bye for now", out.getvalue())
