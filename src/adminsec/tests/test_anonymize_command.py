"""Tests for the ``anonymize`` management command"""

from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from usersec.models import HpcUserCreateRequest, HpcUserCreateRequestEvent

User = get_user_model()


class TestAnonymizeCommand(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create(
            consented_to_terms=True,
            email="maxmustermann@bih.de",
            first_name="Max",
            last_name="Mustermann",
            phone="123-456-789",
            username="user",
            is_staff=True,
            is_superuser=True,
            is_hpcadmin=True,
        )
        self.user.set_password("secret")
        self.user.save()
        self.command = "anonymize"

    def _run(self, *args, **kwargs):
        out, err = StringIO(), StringIO()
        call_command(self.command, *args, stdout=out, stderr=err, **kwargs)
        return out.getvalue(), err.getvalue()

    def test_anonymization(self):
        self._run(self.user.username, "--noinput")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.consented_to_terms)
        self.assertIs(self.user.is_superuser, False)
        self.assertIs(self.user.is_staff, False)
        self.assertIs(self.user.is_hpcadmin, False)
        self.assertEqual(self.user.first_name, "")
        self.assertEqual(self.user.last_name, "Anonymous")
        self.assertEqual(self.user.display_name, "")
        self.assertNotIn("Max", self.user.name)
        self.assertNotEqual(self.user.name, "")
        self.assertEqual(self.user.email, "")
        self.assertEqual(self.user.phone, "")
        self.assertIsNone(self.user.last_login)
        self.assertIsNotNone(self.user.anonymized_at)

    def test_password_unusable(self):
        self._run(self.user.username, "--noinput")
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_usable_password())

    def test_user_not_found(self):
        with self.assertRaisesMessage(CommandError, 'User "no such user" does not exist.'):
            self._run("no such user", "--noinput")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_already_anonymized(self):
        self._run(self.user.username, "--noinput")
        self.user.refresh_from_db()
        with self.assertRaisesMessage(CommandError, "is already anonymized"):
            self._run(self.user.username, "--noinput")

    def test_interactive_mode_abort(self):
        for answer in ("n", "", "no"):
            with self.subTest(answer=answer):
                with mock.patch("builtins.input", return_value=answer):
                    out, _ = self._run(self.user.username)
                self.user.refresh_from_db()
                self.assertTrue(self.user.is_active)
                self.assertTrue(self.user.consented_to_terms)
                self.assertEqual(self.user.first_name, "Max")
                self.assertEqual(self.user.last_name, "Mustermann")
                self.assertEqual(self.user.email, "maxmustermann@bih.de")
                self.assertEqual(self.user.phone, "123-456-789")
                self.assertIn("Operation aborted, bye for now", out)

    def test_interactive_mode_confirm(self):
        with mock.patch("builtins.input", return_value="y"):
            _, err = self._run(self.user.username)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(self.user.email, "")
        self.assertIn("cannot be undone", err)

    def test_noinput_does_not_prompt(self):
        with mock.patch("builtins.input") as mock_input:
            self._run(self.user.username, "--noinput")
        mock_input.assert_not_called()

    def test_create_requests_matched_by_email(self):
        # Mocked to avoid depending on the request model's required fields;
        # replace with real factories if the project has them.
        req = mock.Mock(email=self.user.email)
        qs = mock.MagicMock()
        qs.__iter__.return_value = iter([req])
        with (
            mock.patch.object(HpcUserCreateRequest.objects, "filter", return_value=qs) as m_filter,
            mock.patch.object(
                HpcUserCreateRequestEvent.objects,
                "filter",
                return_value=[],
            ),
        ):
            self._run(self.user.username, "--noinput")
        m_filter.assert_called_once_with(email="maxmustermann@bih.de")
        self.assertEqual(req.email, "")
        req.soft_delete.assert_called_once()

    def test_empty_email_does_not_touch_other_requests(self):
        self.user.email = ""
        self.user.save()
        with (
            mock.patch.object(HpcUserCreateRequest.objects, "filter") as m_req,
            mock.patch.object(HpcUserCreateRequestEvent.objects, "filter") as m_evt,
        ):
            self._run(self.user.username, "--noinput")
        m_req.assert_not_called()
        m_evt.assert_not_called()
