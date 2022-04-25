from django.core import mail

from adminsec.email import (
    send_user_invite,
    send_mail,
    send_user_added_to_project_notification,
    send_project_created_notification,
)
from usersec.tests.factories import HpcUserFactory
from usersec.tests.test_views import TestViewBase


class TestEmail(TestViewBase):
    def setUp(self):
        super().setUp()
        self.hpc_user = HpcUserFactory(primary_group=self.hpc_group)

    def test_send_user_invite(self):
        ret = send_user_invite(
            ["user@example.com"],
            self.hpc_owner,
        )
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_user_added_to_project_notification(self):
        ret = send_user_added_to_project_notification(self.hpc_project)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def send_project_created_notification(self):
        ret = send_project_created_notification(self.hpc_project)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_mail(self):
        ret = send_mail(
            "Subject",
            "Content",
            ["user@example.com"],
        )
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)
