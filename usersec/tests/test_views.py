import json

from django.contrib.messages import get_messages
from django.urls import reverse
from test_plus.test import TestCase

from usersec.models import (
    HpcGroupCreateRequest,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_RETRACTED,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_INITIAL,
)
from usersec.tests.factories import (
    HPCGROUPCREATEREQUESTFORM_DATA_VALID,
    HpcGroupCreateRequestFactory,
    HpcUserFactory,
)


class TestBase(TestCase):
    def setUp(self):
        # Init superuser
        self.superuser = self.make_user("superuser")
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        # Init default user
        self.user = self.make_user("user")
        self.user.save()


class TestHomeView(TestBase):
    """Tests for HomeView."""

    def test_get_no_cluster_user(self):
        with self.login(self.user):
            response = self.client.get(reverse("home"))
            self.assertRedirects(response, reverse("usersec:orphan-user"))

    def test_get_cluster_user(self):
        HpcUserFactory(user=self.user)

        with self.login(self.user):
            response = self.client.get(reverse("home"))
            self.assertRedirects(response, reverse("usersec:dummy"))


class TestOrphanUserView(TestBase):
    """Tests for OrphanUserView."""

    def test_get(self):
        with self.login(self.user):
            response = self.client.get(reverse("usersec:orphan-user"))
            self.assertEqual(response.status_code, 200)

    def test_post_form_valid(self):
        with self.login(self.user):
            data = dict(HPCGROUPCREATEREQUESTFORM_DATA_VALID)
            response = self.client.post(
                reverse("usersec:orphan-user"), data=data
            )
            request = HpcGroupCreateRequest.objects.first()
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request.uuid},
                ),
            )
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Group request submitted.")

    def test_post_form_invalid(self):
        with self.login(self.user):
            data = dict(HPCGROUPCREATEREQUESTFORM_DATA_VALID)
            data["resources_requested"] = ""
            response = self.client.post(
                reverse("usersec:orphan-user"), data=data
            )
            self.assertEqual(
                response.context["form"].errors["resources_requested"][0],
                "This field is required.",
            )


class TestHpcGroupCreateRequestDetailView(TestBase):
    """Tests for HpcGroupCreateRequestDetailView."""

    def test_get(self):
        request = HpcGroupCreateRequestFactory(requester=self.user)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
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

    def test_get_retracted(self):
        request = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_RETRACTED
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])

    def test_get_denied(self):
        request = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_DENIED
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])


class TestHpcGroupCreateRequestUpdateView(TestBase):
    """Tests for HpcGroupCreateRequestUpdateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(requester=self.user)

    def test_get(self):
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupcreaterequest-update",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"]["resources_requested"].value(),
                json.dumps(self.obj.resources_requested),
            )
            self.assertEqual(
                response.context["form"]["description"].value(),
                self.obj.description,
            )
            # TODO get this damn time zone issue solved
            # self.assertEqual(response.context["form"]["expiration"].value(), self.obj.expiration)
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])
            self.assertEqual(
                response.context["comment_history"],
                self.obj.get_comment_history(),
            )

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": '{"updated": 400}',
            "description": "description changed",
            "expiration": "2050-01-01",
        }

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    "usersec:hpcgroupcreaterequest-update",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
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
            # TODO Sort out timezone issue
            # self.assertEqual(self.obj.expiration, update["expiration"])

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Group request updated.")

    def test_post_fail(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": "",
            "description": "description changed",
            "expiration": "2050-01-01",
        }

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    "usersec:hpcgroupcreaterequest-update",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
                update,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"].errors["resources_requested"],
                ["This field is required."],
            )


class TestHpcGroupCreateRequestRetractView(TestBase):
    """Tests for HpcGroupCreateRequestRetractView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(requester=self.user)

    def test_get(self):
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupcreaterequest-retract",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    "usersec:hpcgroupcreaterequest-retract",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Request successfully retracted."
            )

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)


class TestPendingGroupRequestReactivateView(TestBase):
    """Tests for PendingGroupRequestReactivateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_RETRACTED
        )

    def test_get(self):
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupcreaterequest-reactivate",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                )
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Request successfully re-activated."
            )

            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
