import json

from django.contrib.messages import get_messages
from django.urls import reverse

from usersec.models import (
    HpcGroupCreateRequest,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_RETRACTED,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_APPROVED,
)
from usersec.tests.factories import HpcGroupCreateRequestFactory
from usersec.tests.test_views import TestViewBase


class TestAdminView(TestViewBase):

    """Tests for AdminView."""

    def test_get(self):
        HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_ACTIVE
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("adminsec:overview"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                list(response.context["hpcgroupcreaterequests"]),
                list(HpcGroupCreateRequest.objects.active()),
            )


class TestHpcGroupCreateRequestDetailView(TestViewBase):

    """Tests for HpcGroupCreateRequestDetailView."""

    def test_get(self):
        request = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_ACTIVE
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["comment_history"],
                request.get_comment_history(),
            )
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_decided"])
            self.assertTrue(response.context["admin"])

    def test_get_retracted(self):
        request = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_RETRACTED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])

    def test_get_denied(self):
        request = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_DENIED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])

    def test_get_approved(self):
        request = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_APPROVED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])


class TestHpcGroupCreateRequestRevisionView(TestViewBase):

    """Tests for HpcGroupCreateRequestRevisionView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-revision",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertNotIn("resources_requested", response.context["form"])
            self.assertNotIn("description", response.context["form"])
            self.assertNotIn("expiration", response.context["form"])
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])
            self.assertEqual(
                response.context["comment_history"],
                self.obj.get_comment_history(),
            )

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": json.dumps(self.obj.resources_requested),
            "description": self.obj.description,
            "expiration": self.obj.expiration,
        }

        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcgroupcreaterequest-revision",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(self.obj.description, update["description"])
            self.assertEqual(self.obj.editor, self.user_hpcadmin)
            self.assertEqual(self.obj.requester, self.user)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Revision requested.")


class TestHpcGroupCreateRequestApproveView(TestViewBase):

    """Tests for HpcGroupCreateRequestApproveView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-approve",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcgroupcreaterequest-approve",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Request successfully approved.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)


class TestHpcGroupCreateRequestDenyView(TestViewBase):

    """Tests for HpcGroupCreateRequestDenyView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-deny",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcgroupcreaterequest-deny",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Request successfully denied.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)
