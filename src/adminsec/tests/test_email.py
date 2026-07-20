from django.core import mail

# TODO import and test new functions
from adminsec.email import (
    send_mail,
    send_notification_admin_request,
    send_notification_manager_group_created,
    send_notification_manager_group_request,
    send_notification_manager_project_created,
    send_notification_manager_project_request,
    send_notification_manager_request_approved,
    send_notification_manager_request_denied,
    send_notification_manager_revision_required,
    send_notification_manager_user_decided_invitation,
    send_notification_user_consent,
    send_notification_user_invitation,
    send_notification_user_welcome_mail,
)
from usersec.tests.factories import (
    HpcGroupCreateRequestFactory,
    HpcGroupInvitationFactory,
    HpcProjectCreateRequestFactory,
    HpcProjectInvitationFactory,
    HpcUserChangeRequestFactory,
    HpcUserCreateRequestFactory,
)
from usersec.tests.test_views import TestViewBase


class TestEmail(TestViewBase):
    def setUp(self):
        super().setUp()
        self.hpc_user_create_request = HpcUserCreateRequestFactory(
            requester=self.user, group=self.hpc_group
        )
        self.hpc_group_create_request = HpcGroupCreateRequestFactory(requester=self.user)
        self.hpc_project_create_request = HpcProjectCreateRequestFactory(requester=self.user)
        self.hpc_user_change_request = HpcUserChangeRequestFactory(requester=self.user)
        self.group_invitation = HpcGroupInvitationFactory(
            hpcusercreaterequest=self.hpc_user_create_request
        )
        self.project_invitation = HpcProjectInvitationFactory(
            hpcprojectcreaterequest=self.hpc_project_create_request, user=self.hpc_member
        )

    def test_send_notification_admin_request(self):
        ret = send_notification_admin_request(self.hpc_user_create_request)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_manager_group_request(self):
        ret = send_notification_manager_group_request(self.hpc_group_create_request)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_manager_group_created(self):
        ret = send_notification_manager_group_created(self.hpc_group_create_request, self.hpc_group)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_manager_project_request(self):
        ret = send_notification_manager_project_request(self.hpc_project_create_request)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_manager_project_created(self):
        ret = send_notification_manager_project_created(
            self.hpc_project_create_request, self.hpc_project
        )
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_manager_change_request_approved(self):
        ret = send_notification_manager_request_approved(self.hpc_user_change_request)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_manager_user_decided_invitation(self):
        ret = send_notification_manager_user_decided_invitation(self.group_invitation)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_manager_revision_required(self):
        ret = send_notification_manager_revision_required(self.hpc_user_create_request)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_manager_request_denied(self):
        ret = send_notification_manager_request_denied(self.hpc_user_create_request)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_user_invitation(self):
        ret = send_notification_user_invitation(self.group_invitation)
        self.assertEqual(ret, 1)
        ret = send_notification_user_invitation(self.project_invitation)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_send_notification_user_welcome_mail(self):
        ret = send_notification_user_welcome_mail(self.hpc_member)
        self.assertEqual(ret, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_notification_user_consent(self):
        ret = send_notification_user_consent(self.user)
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
