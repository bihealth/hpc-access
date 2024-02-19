import json

from django.conf import settings
from django.contrib.messages import get_messages
from django.core import mail
from django.urls import reverse
from test_plus.test import TestCase

from usersec.models import (
    INVITATION_STATUS_ACCEPTED,
    INVITATION_STATUS_PENDING,
    INVITATION_STATUS_REJECTED,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_INITIAL,
    REQUEST_STATUS_RETRACTED,
    HpcGroupCreateRequest,
    HpcProjectChangeRequest,
    HpcProjectCreateRequest,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
)
from usersec.tests.factories import (
    HPCGROUPCREATEREQUEST_FORM_DATA_VALID,
    HPCPROJECTCHANGEREQUEST_FORM_DATA_VALID,
    HPCPROJECTCREATEREQUEST_FORM_DATA_VALID,
    HPCUSERCHANGEREQUEST_FORM_DATA_VALID,
    HPCUSERCREATEREQUEST_FORM_DATA_VALID,
    HpcGroupChangeRequestFactory,
    HpcGroupCreateRequestFactory,
    HpcGroupFactory,
    HpcGroupInvitationFactory,
    HpcProjectChangeRequestFactory,
    HpcProjectCreateRequestFactory,
    HpcProjectFactory,
    HpcProjectInvitationFactory,
    HpcUserChangeRequestFactory,
    HpcUserCreateRequestFactory,
    HpcUserFactory,
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
        self.user.email = "user@example.com"
        self.user.save()

        # Create group and owner
        self.user_owner = self.make_user("owner")
        self.user_owner.email = "owner@example.com"
        self.user_owner.name = "AG Owner"
        self.user_owner.save()

        self.hpc_group = HpcGroupFactory()
        self.hpc_owner = HpcUserFactory(
            user=self.user_owner, primary_group=self.hpc_group, creator=self.user_hpcadmin
        )
        self.hpc_group.owner = self.hpc_owner
        self.hpc_group.save()

        self.user_member = self.make_user("member")
        self.user_member.name = "AG Member"
        self.user_member.email = "member@example.com"
        self.user_member.save()

        self.hpc_member = HpcUserFactory(
            user=self.user_member, primary_group=self.hpc_group, creator=self.user_hpcadmin
        )

        # Create project
        self.hpc_project = HpcProjectFactory(group=self.hpc_group)
        self.hpc_project.members.add(self.hpc_owner)
        self.hpc_project.get_latest_version().members.add(self.hpc_owner)


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
            data = dict(HPCGROUPCREATEREQUEST_FORM_DATA_VALID)
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
            self.assertEqual(str(messages[0]), "Successfully submitted request for group creation.")

            self.assertEqual(len(mail.outbox), 2)

    def test_post_form_invalid(self):
        with self.login(self.user):
            data = dict(HPCGROUPCREATEREQUEST_FORM_DATA_VALID)
            data["resources_requested"] = ""
            response = self.client.post(reverse("usersec:orphan-user"), data=data)
            self.assertEqual(
                response.context["form"].errors["resources_requested"][0],
                "This field is required.",
            )
            self.assertEqual(len(mail.outbox), 0)


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
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

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
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

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
            self.assertTrue(response.context["is_decided"])
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

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
            self.assertTrue(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])


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

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": '{"updated": 400}',
            "description": "description changed",
            "tier1_scratch": 100,
            "tier1_work": 200,
            "tier2_mirrored": 300,
            "tier2_unmirrored": 400,
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
            self.assertEqual(str(messages[0]), "Successfully updated request for group creation.")

            self.assertEqual(len(mail.outbox), 0)

    def test_post_fail(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": "",
            "description": "description changed",
            "tier1_scratch": 100,
            "tier1_work": 200,
            "tier2_mirrored": 300,
            "tier2_unmirrored": 400,
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
            self.assertEqual(str(messages[0]), "Successfully retracted request for group creation.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)

            self.assertEqual(len(mail.outbox), 0)


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
            self.assertEqual(
                str(messages[0]), "Successfully re-activated request for group creation."
            )

            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)


class TestHpcGroupChangeRequestDetailView(TestViewBase):
    """Tests for HpcGroupChangeRequestDetailView."""

    def test_get(self):
        request = HpcGroupChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_ACTIVE, group=self.hpc_group
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupchangerequest-detail",
                    kwargs={"hpcgroupchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_retracted(self):
        request = HpcGroupChangeRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_RETRACTED
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupchangerequest-detail",
                    kwargs={"hpcgroupchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_denied(self):
        request = HpcGroupChangeRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_DENIED
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupchangerequest-detail",
                    kwargs={"hpcgroupchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_approved(self):
        request = HpcGroupChangeRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_APPROVED
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupchangerequest-detail",
                    kwargs={"hpcgroupchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])


class TestHpcGroupChangeRequestUpdateView(TestViewBase):
    """Tests for HpcGroupChangeRequestUpdateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupChangeRequestFactory(requester=self.user_owner, group=self.hpc_group)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupchangerequest-update",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
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
            self.assertEqual(response.context["form"]["description"].value(), self.obj.description)
            self.assertTrue(response.context["update"])

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": '{"updated": 400}',
            "description": "description changed",
            "tier1_scratch": 100,
            "tier1_work": 200,
            "tier2_mirrored": 300,
            "tier2_unmirrored": 400,
            "expiration": "2050-01-01",
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcgroupchangerequest-update",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcgroupchangerequest-detail",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(self.obj.description, update["description"])
            self.assertEqual(self.obj.editor, self.user_owner)
            self.assertEqual(self.obj.requester, self.user_owner)
            # TODO Sort out timezone issue
            # self.assertEqual(self.obj.expiration, update["expiration"])

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully updated request for group update.")

            self.assertEqual(len(mail.outbox), 0)

    def test_post_fail(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": "",
            "description": "description changed",
            "tier1_scratch": 100,
            "tier1_work": 200,
            "tier2_mirrored": 300,
            "tier2_unmirrored": 400,
            "expiration": "2050-01-01",
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcgroupchangerequest-update",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
                update,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"].errors["resources_requested"],
                ["This field is required."],
            )


class TestHpcGroupChangeRequestRetractView(TestViewBase):
    """Tests for HpcGroupChangeRequestRetractView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupChangeRequestFactory(requester=self.user_owner, group=self.hpc_group)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupchangerequest-retract",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcgroupchangerequest-retract",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcgroupchangerequest-detail",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully retracted request for group update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)

            self.assertEqual(len(mail.outbox), 0)


class TestHpcGroupChangeRequestReactivateView(TestViewBase):
    """Tests for HpcGroupChangeRequestReactivateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_RETRACTED, group=self.hpc_group
        )

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupchangerequest-reactivate",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                )
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcgroupchangerequest-detail",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Successfully re-activated request for group update."
            )

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


class TestHpcUserDetailView(TestViewBase):
    """Tests for HpcUserDetailView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuser-detail",
                    kwargs={"hpcuser": self.hpc_owner.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.hpc_owner)


class TestHpcGroupDetailView(TestViewBase):
    """Tests for HpcGroupDetailView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse("usersec:hpcgroup-detail", kwargs={"hpcgroup": self.hpc_group.uuid})
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.hpc_group)


class TestHpcProjectDetailView(TestViewBase):
    """Tests for HpcProjectDetailView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse("usersec:hpcproject-detail", kwargs={"hpcproject": self.hpc_project.uuid})
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.hpc_project)


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
            data = dict(HPCUSERCREATEREQUEST_FORM_DATA_VALID)
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
            self.assertEqual(str(messages[0]), "Couldn't submitted request for user creation.")

            self.assertEqual(len(mail.outbox), 1)

    def test_post_form_invalid(self):
        with self.login(self.user_owner):
            data = dict(HPCUSERCREATEREQUEST_FORM_DATA_VALID)
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
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

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
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

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
            self.assertTrue(response.context["is_decided"])
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_approved(self):
        request = HpcUserCreateRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_APPROVED, group=self.hpc_group
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])


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

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": '{"updated": 400}',
            "tier1_scratch": 100,
            "tier1_work": 200,
            "tier2_mirrored": 300,
            "tier2_unmirrored": 400,
            "email": "other@" + settings.INSTITUTE_EMAIL_DOMAINS.split(",")[0],
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
            self.assertEqual(str(messages[0]), "Successfully updated request for user creation.")

            self.assertEqual(len(mail.outbox), 1)

    def test_post_fail(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": "",
            "tier1_scratch": 100,
            "tier1_work": 200,
            "tier2_mirrored": 300,
            "tier2_unmirrored": 400,
            "email": "other@" + settings.INSTITUTE_EMAIL_DOMAINS.split(",")[0],
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
            self.assertEqual(str(messages[0]), "Successfully retracted request for user creation.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)

            self.assertEqual(len(mail.outbox), 0)


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
            self.assertEqual(
                str(messages[0]), "Successfully re-activated request for user creation."
            )

            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)


class TestHpcUserChangeRequestCreateView(TestViewBase):
    """Tests for HpcUserChangeRequestCreateView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuserchangerequest-create", kwargs={"hpcuser": self.hpc_member.uuid}
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_post_form_valid(self):
        with self.login(self.user_owner):
            data = dict(HPCUSERCHANGEREQUEST_FORM_DATA_VALID)
            response = self.client.post(
                reverse(
                    "usersec:hpcuserchangerequest-create", kwargs={"hpcuser": self.hpc_member.uuid}
                ),
                data=data,
            )
            request = HpcUserChangeRequest.objects.first()
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": request.uuid},
                ),
            )
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully submitted request for user update.")

            self.assertEqual(len(mail.outbox), 1)

    def test_post_form_invalid(self):
        with self.login(self.user_owner):
            data = dict(HPCUSERCHANGEREQUEST_FORM_DATA_VALID)
            data["expiration"] = ""
            response = self.client.post(
                reverse(
                    "usersec:hpcuserchangerequest-create", kwargs={"hpcuser": self.hpc_member.uuid}
                ),
                data=data,
            )
            self.assertEqual(
                response.context["form"].errors["expiration"][0],
                "This field is required.",
            )


class TestHpcUserChangeRequestDetailView(TestViewBase):
    """Tests for HpcUserChangeRequestDetailView."""

    def test_get(self):
        request = HpcUserChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_ACTIVE, user=self.hpc_member
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_retracted(self):
        request = HpcUserChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_RETRACTED, user=self.hpc_member
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_denied(self):
        request = HpcUserChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_DENIED, user=self.hpc_member
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_approved(self):
        request = HpcUserChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_APPROVED, user=self.hpc_member
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])


class TestHpcUserChangeRequestUpdateView(TestViewBase):
    """Tests for HpcUserChangeRequestUpdateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserChangeRequestFactory(requester=self.user_owner, user=self.hpc_member)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuserchangerequest-update",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            # TODO
            # self.assertEqual(
            #     response.context["form"]["expiration"].value(),
            #     self.obj.expiration
            # )
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "expiration": "2050-01-01",
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcuserchangerequest-update",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(self.obj.editor, self.user_owner)
            self.assertEqual(self.obj.requester, self.user_owner)
            # TODO Sort out timezone issue
            # self.assertEqual(self.obj.expiration, update["expiration"])

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully updated request for user update.")

            self.assertEqual(len(mail.outbox), 0)

    def test_post_fail(self):
        update = {
            "comment": "I made a comment!",
            "expiration": "",
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcuserchangerequest-update",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
                update,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"].errors["expiration"],
                ["This field is required."],
            )
            self.assertEqual(len(mail.outbox), 0)


class TestHpcUserChangeRequestRetractView(TestViewBase):
    """Tests for HpcUserChangeRequestRetractView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserChangeRequestFactory(requester=self.user_owner, user=self.hpc_member)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuserchangerequest-retract",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcuserchangerequest-retract",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully retracted request for user update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)

            self.assertEqual(len(mail.outbox), 0)


class TestHpcUserChangeRequestRectivateView(TestViewBase):
    """Tests for HpcUserChangeRequestReactivateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserChangeRequestFactory(
            requester=self.user_owner, user=self.hpc_member, status=REQUEST_STATUS_RETRACTED
        )

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcuserchangerequest-reactivate",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                )
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully re-activated request for user update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)


class TestHpcProjectCreateRequestCreateView(TestViewBase):
    """Tests for HpcProjectCreateRequestCreateView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectcreaterequest-create",
                    kwargs={"hpcgroup": self.hpc_group.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_post_form_valid(self):
        with self.login(self.user_owner):
            data = dict(HPCPROJECTCREATEREQUEST_FORM_DATA_VALID)
            data["members"] = [self.hpc_owner.id]
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectcreaterequest-create",
                    kwargs={"hpcgroup": self.hpc_group.uuid},
                ),
                data=data,
            )
            self.assertEqual(HpcProjectCreateRequest.objects.count(), 1)
            request = HpcProjectCreateRequest.objects.first()
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": request.uuid},
                ),
            )
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Successfully submitted request for project creation."
            )

            self.assertEqual(len(mail.outbox), 2)

    def test_post_form_invalid(self):
        with self.login(self.user_owner):
            data = dict(HPCPROJECTCREATEREQUEST_FORM_DATA_VALID)
            data["members"] = []
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectcreaterequest-create",
                    kwargs={"hpcgroup": self.hpc_group.uuid},
                ),
                data=data,
            )
            self.assertEqual(
                response.context["form"].errors["members"][0],
                "This field is required.",
            )

            self.assertEqual(len(mail.outbox), 0)


class TestHpcProjectCreateRequestDetailView(TestViewBase):
    """Tests for HpcProjectCreateRequestDetailView."""

    def test_get(self):
        request = HpcProjectCreateRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_ACTIVE, group=self.hpc_group
        )
        request.members.add(self.hpc_owner)

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_retracted(self):
        request = HpcProjectCreateRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_RETRACTED, group=self.hpc_group
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_denied(self):
        request = HpcProjectCreateRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_DENIED, group=self.hpc_group
        )
        request.members.add(self.hpc_owner)

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_approved(self):
        request = HpcProjectCreateRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_APPROVED, group=self.hpc_group
        )
        request.members.add(self.hpc_owner)

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])


class TestHpcProjectCreateRequestUpdateView(TestViewBase):
    """Tests for HpcProjectCreateRequestUpdateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectCreateRequestFactory(requester=self.user_owner, group=self.hpc_group)
        self.obj.members.add(self.hpc_owner)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectcreaterequest-update",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
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
            self.assertEqual(
                response.context["form"]["name"].value(),
                self.obj.name,
            )
            self.assertEqual(
                response.context["form"]["members"].value(),
                [m.id for m in self.obj.members.all()],
            )
            # TODO get this damn time zone issue solved
            # self.assertEqual(response.context["form"]["expiration"].value(), self.obj.expiration)
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": '{"updated": 400}',
            "tier1_scratch": 100,
            "tier1_work": 200,
            "tier2_mirrored": 300,
            "tier2_unmirrored": 400,
            "expiration": self.obj.expiration,
            "name": self.obj.name,
            "description": self.obj.description,
            "members": [m.id for m in self.obj.members.all()],
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectcreaterequest-update",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(
                update["description"],
                self.obj.description,
            )
            self.assertEqual(
                update["name"],
                self.obj.name,
            )
            self.assertEqual(
                update["members"],
                [m.id for m in self.obj.members.all()],
            )
            self.assertEqual(self.obj.editor, self.user_owner)
            self.assertEqual(self.obj.requester, self.user_owner)
            # TODO Sort out timezone issue
            # self.assertEqual(self.obj.expiration, update["expiration"])

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully updated request for project creation.")

            self.assertEqual(len(mail.outbox), 0)

    def test_post_fail(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": "",
            "expiration": "2050-01-01",
            "name": self.obj.name,
            "description": self.obj.description,
            "members": [m.id for m in self.obj.members.all()],
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectcreaterequest-update",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
                update,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"].errors["resources_requested"],
                ["This field is required."],
            )
            self.assertEqual(len(mail.outbox), 0)


class TestHpcProjectCreateRequestRetractView(TestViewBase):
    """Tests for HpcProjectCreateRequestRetractView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectCreateRequestFactory(requester=self.user_owner, group=self.hpc_group)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectcreaterequest-retract",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectcreaterequest-retract",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Successfully retracted request for project creation."
            )

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)

            self.assertEqual(len(mail.outbox), 0)


class TestHpcProjectCreateRequestRectivateView(TestViewBase):
    """Tests for HpcProjectCreateRequestReactivateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_RETRACTED
        )

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectcreaterequest-reactivate",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                )
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Successfully re-activated request for project creation."
            )

            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)


class TestHpcProjectChangeRequestCreateView(TestViewBase):
    """Tests for HpcProjectChangeRequestCreateView."""

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectchangerequest-create",
                    kwargs={"hpcproject": self.hpc_project.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_post_form_valid(self):
        with self.login(self.user_owner):
            data = dict(HPCPROJECTCHANGEREQUEST_FORM_DATA_VALID)
            data["members"] = [self.hpc_owner.id, self.hpc_member.id]
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectchangerequest-create",
                    kwargs={"hpcproject": self.hpc_project.uuid},
                ),
                data=data,
            )
            self.assertEqual(HpcProjectChangeRequest.objects.count(), 1)
            request = HpcProjectChangeRequest.objects.first()
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": request.uuid},
                ),
            )
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully submitted request for project update.")

            self.assertEqual(len(mail.outbox), 1)

    def test_post_form_invalid(self):
        with self.login(self.user_owner):
            data = dict(HPCPROJECTCHANGEREQUEST_FORM_DATA_VALID)
            data["members"] = []
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectchangerequest-create",
                    kwargs={"hpcproject": self.hpc_project.uuid},
                ),
                data=data,
            )
            self.assertEqual(
                response.context["form"].errors["members"][0],
                "This field is required.",
            )


class TestHpcProjectChangeRequestDetailView(TestViewBase):
    """Tests for HpcProjectChangeRequestDetailView."""

    def test_get(self):
        request = HpcProjectChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_ACTIVE, project=self.hpc_project
        )
        request.members.add(self.hpc_owner, self.hpc_member)

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertTrue(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_retracted(self):
        request = HpcProjectChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_RETRACTED, project=self.hpc_project
        )

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertTrue(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_denied(self):
        request = HpcProjectChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_DENIED, project=self.hpc_project
        )
        request.members.add(self.hpc_owner, self.hpc_member)

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertTrue(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertFalse(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])

    def test_get_approved(self):
        request = HpcProjectChangeRequestFactory(
            requester=self.user_owner, status=REQUEST_STATUS_APPROVED, project=self.hpc_project
        )
        request.members.add(self.hpc_owner, self.hpc_member)

        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": request.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["is_decided"])
            self.assertFalse(response.context["is_denied"])
            self.assertFalse(response.context["is_retracted"])
            self.assertTrue(response.context["is_approved"])
            self.assertFalse(response.context["is_active"])
            self.assertFalse(response.context["is_revision"])
            self.assertFalse(response.context["is_revised"])


class TestHpcProjectChangeRequestUpdateView(TestViewBase):
    """Tests for HpcProjectCreateRequestUpdateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectChangeRequestFactory(
            requester=self.user_owner, project=self.hpc_project
        )
        self.obj.members.add(self.hpc_owner)

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectchangerequest-update",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
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
            self.assertEqual(
                response.context["form"]["delegate"].value(),
                self.obj.delegate,
            )
            self.assertEqual(
                response.context["form"]["members"].value(),
                [m.id for m in self.obj.members.all()],
            )
            # TODO get this damn time zone issue solved
            # self.assertEqual(response.context["form"]["expiration"].value(), self.obj.expiration)
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": '{"updated": 444}',
            "tier1_scratch": 111,
            "tier1_work": 222,
            "tier2_mirrored": 333,
            "tier2_unmirrored": 444,
            "expiration": self.obj.expiration,
            "description": self.obj.description,
            "members": [m.id for m in self.obj.members.all()],
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectchangerequest-update",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(
                update["description"],
                self.obj.description,
            )
            self.assertEqual(
                update["members"],
                [m.id for m in self.obj.members.all()],
            )
            self.assertEqual(self.obj.editor, self.user_owner)
            self.assertEqual(self.obj.requester, self.user_owner)
            # TODO Sort out timezone issue
            # self.assertEqual(self.obj.expiration, update["expiration"])

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully updated request for project update.")

            self.assertEqual(len(mail.outbox), 0)

    def test_post_fail(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": "",
            "expiration": "2050-01-01",
            "description": self.obj.description,
            "members": [m.id for m in self.obj.members.all()],
        }

        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectchangerequest-update",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
                update,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"].errors["resources_requested"],
                ["This field is required."],
            )


class TestHpcProjectChangeRequestRetractView(TestViewBase):
    """Tests for HpcProjectChangeRequestRetractView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectChangeRequestFactory(
            requester=self.user_owner, project=self.hpc_project
        )

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectchangerequest-retract",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    "usersec:hpcprojectchangerequest-retract",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully retracted request for project update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_INITIAL)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)

            self.assertEqual(len(mail.outbox), 0)


class TestHpcProjectChangeRequestRectivateView(TestViewBase):
    """Tests for HpcProjectChangeRequestReactivateView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectChangeRequestFactory(
            requester=self.user_owner, project=self.hpc_project, status=REQUEST_STATUS_RETRACTED
        )

    def test_get(self):
        with self.login(self.user_owner):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectchangerequest-reactivate",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                )
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Successfully re-activated request for project update."
            )

            self.assertEqual(self.obj.status, REQUEST_STATUS_RETRACTED)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)


class TestHpcGroupInvitationDetailView(TestViewBase):
    """Tests for HpcGroupInvitationDetailView."""

    def setUp(self):
        super().setUp()

        # Invited user
        self.user_invited = self.make_user("invited@" + settings.AUTH_LDAP_USERNAME_DOMAIN)

        # Create HPC group invitation
        self.obj = HpcGroupInvitationFactory(username=self.user_invited.username)
        self.obj.hpcusercreaterequest.group = self.hpc_group
        self.obj.hpcusercreaterequest.save()

    def test_get(self):
        with self.login(self.user_invited):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupinvitation-detail",
                    kwargs={"hpcgroupinvitation": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.obj)


class TestHpcGroupInvitationAcceptView(TestViewBase):
    """Tests for HpcGroupInvitationAcceptView."""

    def setUp(self):
        super().setUp()

        # Invited user
        self.user_invited = self.make_user("invited@" + settings.AUTH_LDAP_USERNAME_DOMAIN)

        # Create HPC group invitation
        self.obj = HpcGroupInvitationFactory(username=self.user_invited.username)
        self.obj.hpcusercreaterequest.group = self.hpc_group
        self.obj.hpcusercreaterequest.requester = self.user_owner
        self.obj.hpcusercreaterequest.save()

    def test_get(self):
        with self.login(self.user_invited):
            self.assertEqual(HpcUser.objects.count(), 2)

            response = self.client.get(
                reverse(
                    "usersec:hpcgroupinvitation-accept",
                    kwargs={"hpcgroupinvitation": self.obj.uuid},
                )
            )

            self.assertEqual(HpcUser.objects.count(), 3)
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": HpcUser.objects.last().uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Invitation successfully accepted and user created.")

            self.assertEqual(self.obj.status, INVITATION_STATUS_PENDING)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, INVITATION_STATUS_ACCEPTED)


class TestHpcGroupInvitationRejectView(TestViewBase):
    """Tests for HpcGroupInvitationRejectView."""

    def setUp(self):
        super().setUp()

        # Invited user
        self.user_invited = self.make_user("invited@" + settings.AUTH_LDAP_USERNAME_DOMAIN)

        # Create HPC group invitation
        self.obj = HpcGroupInvitationFactory(username=self.user_invited.username)
        self.obj.hpcusercreaterequest.group = self.hpc_group
        self.obj.hpcusercreaterequest.requester = self.user_owner
        self.obj.hpcusercreaterequest.save()

    def test_get(self):
        with self.login(self.user_invited):
            response = self.client.get(
                reverse(
                    "usersec:hpcgroupinvitation-reject",
                    kwargs={"hpcgroupinvitation": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.obj)

    def test_post(self):
        with self.login(self.user_invited):
            self.assertEqual(HpcUser.objects.count(), 2)

            response = self.client.post(
                reverse(
                    "usersec:hpcgroupinvitation-reject",
                    kwargs={"hpcgroupinvitation": self.obj.uuid},
                )
            )

            self.assertEqual(HpcUser.objects.count(), 2)
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcgroupinvitation-detail",
                    kwargs={"hpcgroupinvitation": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Invitation successfully rejected.")

            self.assertEqual(self.obj.status, INVITATION_STATUS_PENDING)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, INVITATION_STATUS_REJECTED)

            self.assertEqual(len(mail.outbox), 1)


class TestHpcProjectInvitationAcceptView(TestViewBase):
    """Tests for HpcProjectInvitationAcceptView."""

    def setUp(self):
        super().setUp()

        request = HpcProjectCreateRequestFactory(requester=self.user_owner)

        # Create HPC project invitation
        self.obj = HpcProjectInvitationFactory(
            user=self.hpc_member, project=self.hpc_project, hpcprojectcreaterequest=request
        )

    def test_get(self):
        with self.login(self.user_member):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectinvitation-accept",
                    kwargs={"hpcprojectinvitation": self.obj.uuid},
                )
            )

            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": HpcUser.objects.last().uuid},
                ),
            )

            self.assertEqual(
                list(self.hpc_project.members.all()), [self.hpc_owner, self.hpc_member]
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully joined the project.")

            self.assertEqual(self.obj.status, INVITATION_STATUS_PENDING)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, INVITATION_STATUS_ACCEPTED)


class TestHpcProjectInvitationRejectView(TestViewBase):
    """Tests for HpcProjectInvitationRejectView."""

    def setUp(self):
        super().setUp()

        request = HpcProjectCreateRequestFactory(requester=self.user_owner)

        # Create HPC project invitation
        self.obj = HpcProjectInvitationFactory(
            user=self.hpc_member, project=self.hpc_project, hpcprojectcreaterequest=request
        )

    def test_get(self):
        with self.login(self.user_member):
            response = self.client.get(
                reverse(
                    "usersec:hpcprojectinvitation-reject",
                    kwargs={"hpcprojectinvitation": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.obj)

    def test_post(self):
        with self.login(self.user_member):
            self.assertEqual(HpcUser.objects.count(), 2)

            response = self.client.post(
                reverse(
                    "usersec:hpcprojectinvitation-reject",
                    kwargs={"hpcprojectinvitation": self.obj.uuid},
                )
            )

            self.assertEqual(HpcUser.objects.count(), 2)
            self.assertRedirects(
                response,
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": self.hpc_member.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Invitation successfully rejected.")

            self.assertEqual(self.obj.status, INVITATION_STATUS_PENDING)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, INVITATION_STATUS_REJECTED)

            self.assertEqual(len(mail.outbox), 1)
