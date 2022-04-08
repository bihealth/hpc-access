from django.core import mail

from adminsec.email import send_invite, send_mail
from usersec.tests.factories import HpcUserFactory
from usersec.tests.test_views import TestViewBase


class TestEmail(TestViewBase):
    def setUp(self):
        super().setUp()
        self.hpc_user = HpcUserFactory(primary_group=self.hpc_group)

    def test_send_invite(self):
        with self.login(self.user):
            ret = send_invite(
                ["user@example.com"],
                self.hpc_owner,
            )
            self.assertEqual(ret, 1)
            self.assertEqual(len(mail.outbox), 1)

    def test_send_mail(self):
        with self.login(self.user_hpcadmin):
            ret = send_mail(
                "Subject",
                "Content",
                ["user@example.com"],
            )
            self.assertEqual(ret, 1)
            self.assertEqual(len(mail.outbox), 1)
