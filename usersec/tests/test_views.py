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
    REQUEST_STATUS_APPROVED,
    HpcUserCreateRequest,
)
from usersec.tests.factories import (
    HPCGROUPCREATEREQUESTFORM_DATA_VALID,
    HpcGroupCreateRequestFactory,
    HpcUserFactory,
    HpcGroupFactory,
    HpcUserCreateRequestFactory,
    HPCUSERCREATEREQUESTFORM_DATA_VALID,
)


class TestViewBase(TestCase):
    """Test base for views."""

    def setUp(self):
        # HPC Admin
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()

        # Init default user
        self.user = self.make_user("user@CHARITE")
        self.user.name = "John Doe"
        self.user.save()

        # Create group and owner
        self.user_owner = self.make_user("owner")
        self.hpc_group = HpcGroupFactory()
        self.hpc_owner = HpcUserFactory(user=self.user_owner, primary_group=self.hpc_group)
        self.hpc_group.owner = self.hpc_owner
        self.hpc_group.save()


class TestHomeView(TestViewBase):
    """Tests for HomeView."""

    def test_get_no_cluster_user(self):
        with self.login(self.user):
            response = self.client.get(reverse("home"))
            self.assertRedirects(response, reverse("usersec:orphan-user"))

    def test_get_cluster_user(self):
        hpcuser = HpcUserFactory(user=self.user, primary_group=self.hpc_group)

        with self.login(self.user):
            response = self.client.get(reverse("home"))
            self.assertRedirects(
                response,
                reverse("usersec:hpcuser-overview", kwargs={"hpcuser": hpcuser.uuid}),
            )

    def test_get_admin_user(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("home"))
            self.assertRedirects(response, reverse("adminsec:overview"))


class TestOrphanUserView(TestViewBase):
    """Tests for OrphanUserView."""

    def test_get(self):
        with self.login(self.user):
            response = self.client.get(reverse("usersec:orphan-user"))
            self.assertEqual(response.status_code, 200)

    def test_post_form_valid(self):
        with self.login(self.user):
            data = dict(HPCGROUPCREATEREQUESTFORM_DATA_VALID)
            response = self.client.post(reverse("usersec:orphan-user"), data=data)
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
            response = self.client.post(reverse("usersec:orphan-user"), data=data)
            self.assertEqual(
                response.context["form"].errors["resources_requested"][0],
                "This field is required.",
            )


class TestHpcGroupCreateRequestDetailView(TestViewBase):
    """Tests for HpcGroupCreateRequestDetailView."""

    def test_get(self):
        request = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_ACTIVE)

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
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_decided"])

    def test_get_retracted(self):
        request = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_RETRACTED)

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
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])

    def test_get_denied(self):
        request = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_DENIED)

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
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])

    def test_get_approved(self):
        request = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_APPROVED)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])


class TestHpcGroupCreateRequestUpdateView(TestViewBase):
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
            self.assertEqual(self.obj.editor, self.user)
            self.assertEqual(self.obj.requester, self.user)
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


class TestHpcGroupCreateRequestRetractView(TestViewBase):
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
            self.assertEqual(str(messages[0]), "Request successfully retracted.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)


class TestHpcGroupCreateRequestReactivateView(TestViewBase):
    """Tests for HpcGroupCreateRequestReactivateView."""

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
            self.assertEqual(str(messages[0]), "Request successfully re-activated.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)


class TestHpcUserView(TestViewBase):
    """Tests for HpcUserView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": self.hpc_owner.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.hpc_owner)


class TestHpcGroupView(TestViewBase):
    """Tests for HpcGroupView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse("usersec:hpcgroup-detail", kwargs={"hpcgroup": self.hpc_group.uuid})
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.hpc_group)


class TestHpcUserCreateRequestCreateView(TestViewBase):
    """Tests for HpcUserCreateRequestCreateView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-create", kwargs={"hpcgroup": self.hpc_group.uuid}
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_post_form_valid(self):
        with self.login(self.user_owner):
            data = dict(HPCUSERCREATEREQUESTFORM_DATA_VALID)
            response = self.client.post(
                reverse(
                    "usersec:hpcusercreaterequest-create", kwargs={"hpcgroup": self.hpc_group.uuid}
                ),
                data=data,
            )
            request = HpcUserCreateRequest.objects.first()
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": request.uuid},
                ),
            )
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "User request submitted.")

    def test_post_form_invalid(self):
        with self.login(self.user_owner):
            data = dict(HPCUSERCREATEREQUESTFORM_DATA_VALID)
            data["resources_requested"] = ""
            response = self.client.post(
                reverse(
                    "usersec:hpcusercreaterequest-create", kwargs={"hpcgroup": self.hpc_group.uuid}
                ),
                data=data,
            )
            self.assertEqual(
                response.context["form"].errors["resources_requested"][0],
                "This field is required.",
            )


class TestHpcUserCreateRequestDetailView(TestViewBase):
    """Tests for HpcUserCreateRequestDetailView."""

    def test_get(self):
        request = HpcUserCreateRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_ACTIVE, group=self.hpc_group
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": request.uuid},
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

    def test_get_retracted(self):
        request = HpcUserCreateRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_RETRACTED, group=self.hpc_group
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])

    def test_get_denied(self):
        request = HpcUserCreateRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_DENIED, group=self.hpc_group
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])

    def test_get_approved(self):
        request = HpcUserCreateRequestFactory(
            requester=self.user, status=REQUEST_STATUS_APPROVED, group=self.hpc_group
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertTrue(response.context["is_decided"])


class TestHpcUserCreateRequestUpdateView(TestViewBase):
    """Tests for HpcUserCreateRequestUpdateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserCreateRequestFactory(requester=self.user_owner, group=self.hpc_group)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-update",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"]["resources_requested"].value(),
                json.dumps(self.obj.resources_requested),
            )
            self.assertEqual(
                response.context["form"]["email"].value(),
                self.obj.email,
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
            "email": "other@bih-charite.de",
            "expiration": "2050-01-01",
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcusercreaterequest-update",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(self.obj.email, update["email"])
            self.assertEqual(self.obj.editor, self.user_owner)
            self.assertEqual(self.obj.requester, self.user_owner)
            # TODO Sort out timezone issue
            # self.assertEqual(self.obj.expiration, update["expiration"])

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "User request updated.")

    def test_post_fail(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": "",
            "email": "other@bih-charite.de",
            "expiration": "2050-01-01",
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcusercreaterequest-update",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
                update,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"].errors["resources_requested"],
                ["This field is required."],
            )


class TestHpcUserCreateRequestRetractView(TestViewBase):
    """Tests for HpcUserCreateRequestRetractView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserCreateRequestFactory(requester=self.user_owner, group=self.hpc_group)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-retract",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcusercreaterequest-retract",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Request successfully retracted.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)


class TestHpcUserCreateRequestRectivateView(TestViewBase):
    """Tests for HpcUserCreateRequestReactivateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_RETRACTED
        )

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-reactivate",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                )
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Request successfully re-activated.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
