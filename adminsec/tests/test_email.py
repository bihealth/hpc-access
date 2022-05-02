from django.core import mail

from adminsec.email import (
    send_mail,
    send_notification_object_created,
    send_notification_object_updated,
    send_notification_user_has_invitation,
    send_notification_user_decided_invitation,
    send_notification_request_status_changed,
    send_welcome_mail,
)
from usersec.tests.factories import HpcGroupInvitationFactory, HpcUserCreateRequestFactory
from usersec.tests.test_views import TestViewBase


class TestEmail(TestViewBase):
    def setUp(self):
        super().setUp()
        self.hpc_user_request = HpcUserCreateRequestFactory(
            requester=self.user, group=self.hpc_group
        )
        self.invitation = HpcGroupInvitationFactory(hpcusercreaterequest=self.hpc_user_request)

    def test_send_notification_request_status_changed(self):
        ret = send_notification_request_status_changed(
            ["user@example.com"],
            self.hpc_user_request,
        )
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_user_decided_invitation(self):
        ret = send_notification_user_decided_invitation(self.invitation)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_user_has_invitation(self):
        ret = send_notification_user_has_invitation(self.invitation)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_welcome_mail(self):
        ret = send_welcome_mail(self.hpc_member)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_object_created(self):
        ret = send_notification_object_created(["user@example.com"], self.hpc_project)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_object_updated(self):
        ret = send_notification_object_updated(["user@example.com"], self.hpc_project)
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
