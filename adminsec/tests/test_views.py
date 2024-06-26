import json
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from adminsec.views import (
    convert_to_posix,
    django_to_hpc_username,
    ldap_to_hpc_username,
)
from usersec.models import (
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_RETRACTED,
    TERMS_AUDIENCE_PI,
    TERMS_AUDIENCE_USER,
    HpcGroup,
    HpcGroupCreateRequest,
    HpcGroupInvitation,
    HpcProject,
    HpcProjectInvitation,
    HpcUser,
    TermsAndConditions,
)
from usersec.tests.factories import (
    HpcGroupChangeRequestFactory,
    HpcGroupCreateRequestFactory,
    HpcProjectChangeRequestFactory,
    HpcProjectCreateRequestFactory,
    HpcUserChangeRequestFactory,
    HpcUserCreateRequestFactory,
    HpcUserFactory,
    TermsAndConditionsFactory,
)
from usersec.tests.test_views import TestViewBase

User = get_user_model()


class TestAdminView(TestViewBase):
    """Tests for AdminView."""

    def test_get(self):
        HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_ACTIVE)

        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("adminsec:overview"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                list(response.context["hpcgroupcreaterequests"]),
                list(HpcGroupCreateRequest.objects.active()),
            )


class TestHpcUserDetailView(TestViewBase):
    """Tests for HpcUserDetailView."""

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcuser-detail",
                    kwargs={"hpcuser": self.hpc_owner.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.hpc_owner)


class TestHpcGroupDetailView(TestViewBase):
    """Tests for HpcGroupDetailView."""

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse("adminsec:hpcgroup-detail", kwargs={"hpcgroup": self.hpc_group.uuid})
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.hpc_group)


class TestHpcProjectDetailView(TestViewBase):
    """Tests for HpcProjectDetailView."""

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse("adminsec:hpcproject-detail", kwargs={"hpcproject": self.hpc_project.uuid})
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["object"], self.hpc_project)


class TestHpcGroupCreateRequestDetailView(TestViewBase):
    """Tests for HpcGroupCreateRequestDetailView."""

    def test_get(self):
        request = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_ACTIVE)

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
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
            self.assertTrue(response.context["admin"])

    def test_get_retracted(self):
        request = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_RETRACTED)

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
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

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
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

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-detail",
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


class TestHpcGroupCreateRequestRevisionView(TestViewBase):
    """Tests for HpcGroupCreateRequestRevisionView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_ACTIVE)

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
                reverse("adminsec:overview"),
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
            self.assertEqual(
                str(messages[0]), "Successfully requested revision for group creation."
            )

            self.assertEqual(len(mail.outbox), 1)


class TestHpcGroupCreateRequestApproveView(TestViewBase):
    """Tests for HpcGroupCreateRequestApproveView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_ACTIVE)

    def test_get(self):
        self.obj.name = "doe"
        self.obj.folders = {"null": "/home/doe"}
        self.obj.save()
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupcreaterequest-approve",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    @override_settings(
        INSTITUTE_EMAIL_DOMAINS="charite.de",
        INSTITUTE_USERNAME_SUFFIX="c",
    )
    def test_post(self):
        self.obj.name = "doe"
        self.obj.folders = {"tier1": "/home/doe"}
        self.obj.save()
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcgroupcreaterequest-approve",
                    kwargs={"hpcgroupcreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully approved request for group creation.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)

            hpcgroups = HpcGroup.objects.all()
            hpcusers = HpcUser.objects.all()

            self.assertEqual(hpcgroups.count(), 2)
            self.assertEqual(hpcusers.count(), 3)

            hpcuser = hpcusers.last()  # noqa: E1101
            hpcgroup = hpcgroups.last()  # noqa: E1101
            hpcgroup_version = hpcgroup.version_history.last()

            self.assertEqual(hpcuser.user, self.user)
            self.assertEqual(hpcuser.username, "user_" + settings.INSTITUTE_USERNAME_SUFFIX)
            self.assertEqual(hpcuser.primary_group, hpcgroup)
            self.assertEqual(hpcgroup.owner.user, self.user)
            self.assertEqual(hpcgroup.name, "doe")
            self.assertEqual(hpcgroup.folders, {"tier1": "/home/doe"})
            self.assertEqual(hpcgroup_version.owner, hpcuser)
            self.assertEqual(len(mail.outbox), 2)

    @override_settings(
        INSTITUTE_EMAIL_DOMAINS="charite.de",
        INSTITUTE_USERNAME_SUFFIX="c",
    )
    def test_get_missing_name(self):
        hpcgroups_precount = HpcGroup.objects.count()
        hpcusers_precount = HpcUser.objects.count()
        self.obj.folders = {"tier1": "/path/group"}
        self.obj.save()

        with self.login(self.user_hpcadmin):
            response = self.client.get(
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
            self.assertEqual(
                str(messages[0]),
                "Name is empty. Please submit a name before approving the request.",
            )

            self.assertEqual(HpcGroup.objects.count(), hpcgroups_precount)
            self.assertEqual(HpcUser.objects.count(), hpcusers_precount)

    @override_settings(
        INSTITUTE_EMAIL_DOMAINS="charite.de",
        INSTITUTE_USERNAME_SUFFIX="c",
    )
    def test_get_not_unique_name(self):
        hpcgroups_precount = HpcGroup.objects.count()
        hpcusers_precount = HpcUser.objects.count()
        existing_name = HpcGroup.objects.first().name
        self.obj.folders = {"tier1": "/path/group"}
        self.obj.name = existing_name
        self.obj.save()

        with self.login(self.user_hpcadmin):
            response = self.client.get(
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
            self.assertEqual(
                str(messages[0]),
                f"Group with name '{self.obj.name}' already exists. Please choose another name.",
            )

            self.assertEqual(HpcGroup.objects.count(), hpcgroups_precount)
            self.assertEqual(HpcUser.objects.count(), hpcusers_precount)

    @override_settings(
        INSTITUTE_EMAIL_DOMAINS="charite.de",
        INSTITUTE_USERNAME_SUFFIX="c",
    )
    def test_get_missing_folder(self):
        hpcgroups_precount = HpcGroup.objects.count()
        hpcusers_precount = HpcUser.objects.count()
        self.obj.name = "doe"
        self.obj.save()

        with self.login(self.user_hpcadmin):
            response = self.client.get(
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
            self.assertEqual(
                str(messages[0]),
                "Folders are empty. Please submit paths before approving the request.",
            )

            self.assertEqual(HpcGroup.objects.count(), hpcgroups_precount)
            self.assertEqual(HpcUser.objects.count(), hpcusers_precount)

    @override_settings(
        INSTITUTE_EMAIL_DOMAINS="charite.de",
        INSTITUTE_USERNAME_SUFFIX="c",
    )
    def test_get_not_unique_folder(self):
        hpcgroups_precount = HpcGroup.objects.count()
        hpcusers_precount = HpcUser.objects.count()
        existing_folders = HpcGroup.objects.first().folders
        self.obj.name = "doe"
        self.obj.folders = existing_folders
        self.obj.save()

        with self.login(self.user_hpcadmin):
            response = self.client.get(
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
            self.assertEqual(len(messages), 4)
            self.assertEqual(
                [str(m) for m in messages],
                [
                    (
                        f"Folder with path '{self.obj.folders[n]}' "
                        "already exists. Please choose another path."
                    )
                    for n in ["tier1_work", "tier1_scratch", "tier2_mirrored", "tier2_unmirrored"]
                ],
            )

            self.assertEqual(HpcGroup.objects.count(), hpcgroups_precount)
            self.assertEqual(HpcUser.objects.count(), hpcusers_precount)


class TestHpcGroupCreateRequestDenyView(TestViewBase):
    """Tests for HpcGroupCreateRequestDenyView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_ACTIVE)

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
                data={"comment": "Denied"},
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully denied request for group creation.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.comment, "Denied")
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)

            self.assertEqual(len(mail.outbox), 1)


class TestHpcGroupChangeRequestDetailView(TestViewBase):
    """Tests for HpcGroupChangeRequestDetailView."""

    def test_get(self):
        request = HpcGroupChangeRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupchangerequest-detail",
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
            self.assertTrue(response.context["admin"])

    def test_get_retracted(self):
        request = HpcGroupChangeRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_RETRACTED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupchangerequest-detail",
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

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupchangerequest-detail",
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

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupchangerequest-detail",
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


class TestHpcGroupChangeRequestRevisionView(TestViewBase):
    """Tests for HpcGroupChangeRequestRevisionView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupChangeRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupchangerequest-revision",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertNotIn("resources_requested", response.context["form"])
            self.assertNotIn("description", response.context["form"])
            self.assertNotIn("expiration", response.context["form"])
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])

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
                    "adminsec:hpcgroupchangerequest-revision",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(self.obj.description, update["description"])
            self.assertEqual(self.obj.editor, self.user_hpcadmin)
            self.assertEqual(self.obj.requester, self.user_owner)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully requested revision for group update.")

            self.assertEqual(len(mail.outbox), 1)


class TestHpcGroupChangeRequestApproveView(TestViewBase):
    """Tests for HpcGroupChangeRequestApproveView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupChangeRequestFactory(
            requester=self.user_owner,
            group=self.hpc_group,
            status=REQUEST_STATUS_ACTIVE,
            delegate=self.hpc_member,
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupchangerequest-approve",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    @override_settings(
        INSTITUTE_EMAIL_DOMAINS="charite.de",
        INSTITUTE_USERNAME_SUFFIX="c",
    )
    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcgroupchangerequest-approve",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully approved request for group update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)

            hpcgroups = HpcGroup.objects.all()

            self.assertEqual(hpcgroups.count(), 1)

            hpcgroup = hpcgroups.last()

            self.assertEqual(hpcgroup.delegate, self.hpc_member)
            self.assertEqual(hpcgroup.description, self.obj.description)
            self.assertEqual(hpcgroup.resources_requested, self.obj.resources_requested)

            self.assertEqual(len(mail.outbox), 1)


class TestHpcGroupChangeRequestDenyView(TestViewBase):
    """Tests for HpcGroupChangeRequestDenyView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcGroupChangeRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcgroupchangerequest-deny",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcgroupchangerequest-deny",
                    kwargs={"hpcgroupchangerequest": self.obj.uuid},
                ),
                data={"comment": "Denied"},
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully denied request for group update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.comment, "Denied")
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)

            self.assertEqual(len(mail.outbox), 1)


class TestHpcUserCreateRequestDetailView(TestViewBase):
    """Tests for HpcUserCreateRequestDetailView."""

    def test_get(self):
        request = HpcUserCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
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
            self.assertTrue(response.context["admin"])

    def test_get_retracted(self):
        request = HpcUserCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_RETRACTED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
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
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_DENIED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
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
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_APPROVED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
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


class TestHpcUserCreateRequestRevisionView(TestViewBase):
    """Tests for HpcUserCreateRequestRevisionView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcusercreaterequest-revision",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertNotIn("resources_requested", response.context["form"])
            self.assertNotIn("email", response.context["form"])
            self.assertNotIn("expiration", response.context["form"])
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": json.dumps(self.obj.resources_requested),
            "email": self.obj.email,
            "expiration": self.obj.expiration,
        }

        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcusercreaterequest-revision",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(self.obj.email, update["email"])
            self.assertEqual(self.obj.editor, self.user_hpcadmin)
            self.assertEqual(self.obj.requester, self.user_owner)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully requested revision for user creation.")

            self.assertEqual(len(mail.outbox), 1)


class TestHpcUserCreateRequestApproveView(TestViewBase):
    """Tests for HpcUserCreateRequestApproveView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcusercreaterequest-approve",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    @patch("adminsec.ldap.LdapConnector.connect")
    @patch("adminsec.ldap.LdapConnector.get_ldap_username_domain_by_mail")
    def test_post(self, mock_get_ldap_username_domain_by_mail, mock_connect):
        mock_get_ldap_username_domain_by_mail.return_value = (
            "new_user",
            settings.AUTH_LDAP_USERNAME_DOMAIN,
        )

        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcusercreaterequest-approve",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Request approved and invitation created.")

            self.assertEqual(HpcGroupInvitation.objects.count(), 1)
            invitation = HpcGroupInvitation.objects.first()
            self.assertEqual(invitation.username, "new_user@" + settings.AUTH_LDAP_USERNAME_DOMAIN)

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)

            mock_get_ldap_username_domain_by_mail.assert_called_with(self.obj.email)
            mock_connect.assert_called_once()

            self.assertEqual(len(mail.outbox), 1)


class TestHpcUserCreateRequestDenyView(TestViewBase):
    """Tests for HpcUserCreateRequestDenyView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcusercreaterequest-deny",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcusercreaterequest-deny",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
                data={"comment": "Denied"},
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully denied request for user creation.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.comment, "Denied")
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)

            self.assertEqual(len(mail.outbox), 1)


class TestHpcUserChangeRequestDetailView(TestViewBase):
    """Tests for HpcUserChangeRequestDetailView."""

    def test_get(self):
        request = HpcUserChangeRequestFactory(
            requester=self.user_owner, user=self.hpc_member, status=REQUEST_STATUS_ACTIVE
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcuserchangerequest-detail",
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
            self.assertTrue(response.context["admin"])

    def test_get_retracted(self):
        request = HpcUserChangeRequestFactory(
            requester=self.user_owner, user=self.hpc_member, status=REQUEST_STATUS_RETRACTED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcuserchangerequest-detail",
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
            requester=self.user_owner, user=self.hpc_member, status=REQUEST_STATUS_DENIED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcuserchangerequest-detail",
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
            requester=self.user_owner, user=self.hpc_member, status=REQUEST_STATUS_APPROVED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcuserchangerequest-detail",
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


class TestHpcUserChangeRequestRevisionView(TestViewBase):
    """Tests for HpcUserChangeRequestRevisionView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserChangeRequestFactory(
            requester=self.user_owner, user=self.hpc_member, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcuserchangerequest-revision",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertNotIn("expiration", response.context["form"])
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "expiration": self.obj.expiration,
        }

        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcuserchangerequest-revision",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully requested revision for user update.")

            self.assertEqual(len(mail.outbox), 1)


class TestHpcUserChangeRequestApproveView(TestViewBase):
    """Tests for HpcUserChangeRequestApproveView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserChangeRequestFactory(
            requester=self.user_owner,
            user=self.hpc_member,
            status=REQUEST_STATUS_ACTIVE,
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcuserchangerequest-approve",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    @override_settings(
        INSTITUTE_EMAIL_DOMAINS="charite.de",
        INSTITUTE_USERNAME_SUFFIX="c",
    )
    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcuserchangerequest-approve",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully approved request for user update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)

            hpcusers = HpcUser.objects.all()

            self.assertEqual(hpcusers.count(), 2)

            # hpcuser = hpcusers.last()
            # TODO test expiration date

            self.assertEqual(len(mail.outbox), 1)


class TestHpcUserChangeRequestDenyView(TestViewBase):
    """Tests for HpcUserChangeRequestDenyView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcUserChangeRequestFactory(
            requester=self.user_owner, user=self.hpc_member, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcuserchangerequest-deny",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcuserchangerequest-deny",
                    kwargs={"hpcuserchangerequest": self.obj.uuid},
                ),
                data={"comment": "Denied"},
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully denied request for user update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.comment, "Denied")
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)

            self.assertEqual(len(mail.outbox), 1)


class TestHpcProjectCreateRequestDetailView(TestViewBase):
    """Tests for HpcProjectCreateRequestDetailView."""

    def test_get(self):
        request = HpcProjectCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectcreaterequest-detail",
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
            self.assertTrue(response.context["admin"])

    def test_get_retracted(self):
        request = HpcProjectCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_RETRACTED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectcreaterequest-detail",
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
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_DENIED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectcreaterequest-detail",
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
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_APPROVED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectcreaterequest-detail",
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


class TestHpcProjectCreateRequestRevisionView(TestViewBase):
    """Tests for HpcProjectCreateRequestRevisionView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )
        self.obj.members.add(self.hpc_owner)

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectcreaterequest-revision",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertNotIn("resources_requested", response.context["form"])
            self.assertNotIn("description", response.context["form"])
            self.assertNotIn("expiration", response.context["form"])
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": json.dumps(self.obj.resources_requested),
            "description": self.obj.description,
            "expiration": self.obj.expiration,
            "members": [m.id for m in self.obj.members.all()],
            "name_requested": self.obj.name_requested,
        }

        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcprojectcreaterequest-revision",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(self.obj.description, update["description"])
            self.assertEqual(self.obj.editor, self.user_hpcadmin)
            self.assertEqual(self.obj.requester, self.user_owner)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Successfully requested revision for project creation."
            )

            self.assertEqual(len(mail.outbox), 1)


class TestHpcProjectCreateRequestApproveView(TestViewBase):
    """Tests for HpcProjectCreateRequestApproveView."""

    def setUp(self):
        super().setUp()
        user_delegate = self.make_user("delegate")
        user_delegate.email = "delegate@example.com"
        user_delegate.save()
        self.hpc_delegate = HpcUserFactory(user=user_delegate, primary_group=self.hpc_group)
        self.obj = HpcProjectCreateRequestFactory(
            requester=self.user_owner,
            group=self.hpc_group,
            status=REQUEST_STATUS_ACTIVE,
            name="new_project",
            folders={"tier1": "/path/new_project"},
        )
        self.obj.members.add(self.hpc_member, self.hpc_delegate)

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectcreaterequest-approve",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcprojectcreaterequest-approve",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Successfully approved request for project creation."
            )

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)

            self.assertEqual(HpcProject.objects.count(), 2)
            self.assertEqual(HpcProjectInvitation.objects.count(), 2)

            hpcproject = HpcProject.objects.get(name=self.obj.name)
            hpcproject_version = hpcproject.version_history.last()

            invitation1 = HpcProjectInvitation.objects.first()
            invitation2 = HpcProjectInvitation.objects.last()

            self.assertEqual(invitation1.user, self.hpc_member)
            self.assertEqual(invitation2.user, self.hpc_delegate)

            self.assertEqual(hpcproject.group.owner, self.hpc_owner)
            self.assertEqual(hpcproject.name, self.obj.name)
            self.assertEqual(list(hpcproject.members.all()), [self.hpc_owner])
            self.assertEqual(list(hpcproject_version.members.all()), [self.hpc_owner])

            self.assertEqual(len(mail.outbox), 3)


class TestHpcProjectCreateRequestDenyView(TestViewBase):
    """Tests for HpcProjectCreateRequestDenyView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectCreateRequestFactory(
            requester=self.user_owner, group=self.hpc_group, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectcreaterequest-deny",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcprojectcreaterequest-deny",
                    kwargs={"hpcprojectcreaterequest": self.obj.uuid},
                ),
                data={"comment": "Denied"},
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Request successfully denied.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.comment, "Denied")
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)

            self.assertEqual(len(mail.outbox), 1)


class TestHpcProjectChangeRequestDetailView(TestViewBase):
    """Tests for HpcProjectChangeRequestDetailView."""

    def test_get(self):
        request = HpcProjectChangeRequestFactory(
            requester=self.user_owner, project=self.hpc_project, status=REQUEST_STATUS_ACTIVE
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectchangerequest-detail",
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
            self.assertTrue(response.context["admin"])

    def test_get_retracted(self):
        request = HpcProjectChangeRequestFactory(
            requester=self.user_owner, project=self.hpc_project, status=REQUEST_STATUS_RETRACTED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectchangerequest-detail",
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
            requester=self.user_owner, project=self.hpc_project, status=REQUEST_STATUS_DENIED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectchangerequest-detail",
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
            requester=self.user_owner, project=self.hpc_project, status=REQUEST_STATUS_APPROVED
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectchangerequest-detail",
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


class TestHpcProjectChangeRequestRevisionView(TestViewBase):
    """Tests for HpcProjectChangeRequestRevisionView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectChangeRequestFactory(
            requester=self.user_owner, project=self.hpc_project, status=REQUEST_STATUS_ACTIVE
        )
        self.obj.members.add(self.hpc_owner, self.hpc_member)

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectchangerequest-revision",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertNotIn("resources_requested", response.context["form"])
            self.assertNotIn("description", response.context["form"])
            self.assertNotIn("expiration", response.context["form"])
            self.assertEqual(response.context["form"]["comment"].value(), "")
            self.assertTrue(response.context["update"])

    def test_post(self):
        update = {
            "comment": "I made a comment!",
            "resources_requested": json.dumps(self.obj.resources_requested),
            "description": self.obj.description,
            "expiration": self.obj.expiration,
            "members": [m.id for m in self.obj.members.all()],
        }

        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcprojectchangerequest-revision",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
                update,
            )
            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            self.obj.refresh_from_db()

            self.assertEqual(self.obj.comment, update["comment"])
            self.assertEqual(
                self.obj.resources_requested,
                json.loads(update["resources_requested"]),
            )
            self.assertEqual(self.obj.description, update["description"])
            self.assertEqual(self.obj.editor, self.user_hpcadmin)
            self.assertEqual(self.obj.requester, self.user_owner)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Successfully requested revision for project update."
            )

            self.assertEqual(len(mail.outbox), 1)


class TestHpcProjectChangeRequestApproveView(TestViewBase):
    """Tests for HpcProjectChangeRequestApproveView."""

    def setUp(self):
        super().setUp()
        self.hpc_project.members.add(self.hpc_member)
        self.hpc_project.get_latest_version().members.add(self.hpc_member)

        user_delegate = self.make_user("delegate")
        user_delegate.email = "delegate@example.com"
        user_delegate.save()
        self.hpc_delegate = HpcUserFactory(user=user_delegate, primary_group=self.hpc_group)
        self.obj = HpcProjectChangeRequestFactory(
            requester=self.user_owner,
            project=self.hpc_project,
            status=REQUEST_STATUS_ACTIVE,
            delegate=self.hpc_delegate,
        )
        self.obj.members.add(self.hpc_owner, self.hpc_delegate)
        self.obj.get_latest_version().members.add(self.hpc_owner, self.hpc_delegate)

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectchangerequest-approve",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcprojectchangerequest-approve",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully approved request for project update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)

            self.assertEqual(HpcProject.objects.count(), 1)
            self.assertEqual(HpcProjectInvitation.objects.count(), 1)

            self.hpc_project.refresh_from_db()
            hpcproject_version = self.hpc_project.get_latest_version()

            invitation1 = HpcProjectInvitation.objects.first()

            self.assertEqual(invitation1.user, self.hpc_delegate)

            self.assertEqual(self.hpc_project.group.owner, self.hpc_owner)
            self.assertEqual(self.hpc_delegate, self.hpc_delegate)
            self.assertEqual(list(self.hpc_project.members.all()), [self.hpc_owner])
            self.assertEqual(list(hpcproject_version.members.all()), [self.hpc_owner])

            self.assertEqual(len(mail.outbox), 2)


class TestHpcProjectChangeRequestDenyView(TestViewBase):
    """Tests for HpcProjectChangeRequestDenyView."""

    def setUp(self):
        super().setUp()
        self.obj = HpcProjectChangeRequestFactory(
            requester=self.user_owner, project=self.hpc_project, status=REQUEST_STATUS_ACTIVE
        )

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:hpcprojectchangerequest-deny",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcprojectchangerequest-deny",
                    kwargs={"hpcprojectchangerequest": self.obj.uuid},
                ),
                data={"comment": "Denied"},
            )

            self.assertRedirects(
                response,
                reverse("adminsec:overview"),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully denied request for project update.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.comment, "Denied")
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)

            self.assertEqual(len(mail.outbox), 1)


class TestTermsAndConditionsListView(TestViewBase):
    """Tests for TermsAndConditionsListView."""

    def test_get(self):
        self.terms_all = TermsAndConditionsFactory()
        self.terms_pi = TermsAndConditionsFactory(title="For PIs", audience=TERMS_AUDIENCE_PI)
        self.terms_users = TermsAndConditionsFactory(
            title="For Users", audience=TERMS_AUDIENCE_USER
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("adminsec:termsandconditions-list"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["object_list"]), 3)
            self.assertListEqual(
                list(response.context["object_list"]),
                [self.terms_all, self.terms_pi, self.terms_users],
            )
            self.assertTrue(response.context["not_published"])

    def test_get_published(self):
        self.terms_all = TermsAndConditionsFactory()
        self.terms_pi = TermsAndConditionsFactory(title="For PIs", audience=TERMS_AUDIENCE_PI)
        self.terms_users = TermsAndConditionsFactory(
            title="For Users", audience=TERMS_AUDIENCE_USER
        )
        TermsAndConditions.objects.all().update(date_published=timezone.now())

        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("adminsec:termsandconditions-list"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["object_list"]), 3)
            self.assertListEqual(
                list(response.context["object_list"]),
                [self.terms_all, self.terms_pi, self.terms_users],
            )
            self.assertFalse(response.context["not_published"])

    def test_get_not_all_published(self):
        self.terms_all = TermsAndConditionsFactory(date_published=timezone.now())
        self.terms_pi = TermsAndConditionsFactory(title="For PIs", audience=TERMS_AUDIENCE_PI)
        self.terms_users = TermsAndConditionsFactory(
            title="For Users", audience=TERMS_AUDIENCE_USER
        )

        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("adminsec:termsandconditions-list"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["object_list"]), 3)
            self.assertListEqual(
                list(response.context["object_list"]),
                [self.terms_all, self.terms_pi, self.terms_users],
            )
            self.assertTrue(response.context["not_published"])

    def test_get_edit_after_published(self):
        self.terms_all = TermsAndConditionsFactory()
        self.terms_pi = TermsAndConditionsFactory(title="For PIs", audience=TERMS_AUDIENCE_PI)
        self.terms_users = TermsAndConditionsFactory(
            title="For Users", audience=TERMS_AUDIENCE_USER
        )
        TermsAndConditions.objects.all().update(date_published=timezone.now())
        self.terms_all.text = "Updated"
        self.terms_all.save()

        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("adminsec:termsandconditions-list"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["object_list"]), 3)
            self.assertListEqual(
                list(response.context["object_list"]),
                [self.terms_pi, self.terms_users, self.terms_all],
            )
            self.assertTrue(response.context["not_published"])

    def test_get_empty(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("adminsec:termsandconditions-list"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["object_list"]), 0)


class TestTermsAndConditionsCreateView(TestViewBase):
    """Tests for TermsAndConditionsCreateView."""

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(reverse("adminsec:termsandconditions-create"))

            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        terms = {
            "title": "Terms and Conditions",
            "text": "Content",
            "audience": TERMS_AUDIENCE_USER,
        }

        with self.login(self.user_hpcadmin):
            self.assertEqual(TermsAndConditions.objects.count(), 0)

            response = self.client.post(
                reverse("adminsec:termsandconditions-create"),
                terms,
            )

            self.assertRedirects(
                response,
                reverse("adminsec:termsandconditions-list"),
            )

            self.assertEqual(TermsAndConditions.objects.count(), 1)

            terms = TermsAndConditions.objects.first()
            self.assertEqual(terms.text, "Content")
            self.assertEqual(terms.audience, TERMS_AUDIENCE_USER)


class TestTermsAndConditionsUpdateView(TestViewBase):
    """Tests for TermsAndConditionsUpdateView."""

    def setUp(self):
        super().setUp()
        self.terms = TermsAndConditionsFactory()

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:termsandconditions-update",
                    kwargs={"termsandconditions": self.terms.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        terms = {
            "title": self.terms.title,
            "text": "updated",
            "audience": TERMS_AUDIENCE_USER,
        }
        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:termsandconditions-update",
                    kwargs={"termsandconditions": self.terms.uuid},
                ),
                terms,
            )

            self.assertRedirects(
                response,
                reverse("adminsec:termsandconditions-list"),
            )

            self.terms.refresh_from_db()
            self.assertEqual(TermsAndConditions.objects.count(), 1)
            self.assertEqual(self.terms.text, "updated")
            self.assertEqual(self.terms.audience, TERMS_AUDIENCE_USER)


class TestTermsAndConditionsDeleteView(TestViewBase):
    """Tests for TermsAndConditionsDeleteView."""

    def setUp(self):
        super().setUp()
        self.terms = TermsAndConditionsFactory()

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:termsandconditions-delete",
                    kwargs={"termsandconditions": self.terms.uuid},
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        self.assertEqual(TermsAndConditions.objects.count(), 1)

        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:termsandconditions-delete",
                    kwargs={"termsandconditions": self.terms.uuid},
                )
            )

            self.assertRedirects(
                response,
                reverse("adminsec:termsandconditions-list"),
            )

            self.assertEqual(TermsAndConditions.objects.count(), 0)


class TestTermsAndConditionsPublishView(TestViewBase):
    """Tests for TermsAndConditionsPublishView."""

    def setUp(self):
        super().setUp()
        self.terms = TermsAndConditionsFactory()
        self.user.consented_to_terms = True
        self.user.save()
        self.user_owner.consented_to_terms = True
        self.user_owner.save()

    def test_get(self):
        with self.login(self.user_hpcadmin):
            response = self.client.get(
                reverse(
                    "adminsec:termsandconditions-publish",
                )
            )

            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["form"])

    def test_post(self):
        with self.login(self.user_hpcadmin):
            self.assertIsNone(self.terms.date_published)
            self.assertTrue(self.user.consented_to_terms)
            self.assertTrue(self.user_owner.consented_to_terms)

            response = self.client.post(
                reverse(
                    "adminsec:termsandconditions-publish",
                )
            )

            self.assertRedirects(
                response,
                reverse("adminsec:termsandconditions-list"),
            )

            self.terms.refresh_from_db()
            self.user.refresh_from_db()
            self.user_owner.refresh_from_db()

            self.assertIsNotNone(self.terms.date_published)
            self.assertFalse(self.user.consented_to_terms)
            self.assertFalse(self.user_owner.consented_to_terms)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Successfully published the terms and conditions.")

            self.assertEqual(
                len(mail.outbox),
                User.objects.all()
                .exclude(is_hpcadmin=True)
                .exclude(is_superuser=True)
                .exclude(is_staff=True)
                .count(),
            )


class TestFunctions(TestViewBase):
    """Test non-view related functions."""

    def test_ldap_to_hpc_username_institute1(self):
        username = "user"
        domain = settings.AUTH_LDAP_USERNAME_DOMAIN
        self.assertEqual(
            ldap_to_hpc_username(username, domain), "user_" + settings.INSTITUTE_USERNAME_SUFFIX
        )

    def test_ldap_to_hpc_username_institute2(self):
        username = "user"
        domain = settings.AUTH_LDAP2_USERNAME_DOMAIN
        self.assertEqual(
            ldap_to_hpc_username(username, domain), "user_" + settings.INSTITUTE2_USERNAME_SUFFIX
        )

    def test_ldap_to_hpc_username_invalid_string(self):
        username = "user"
        domain = "UNKNOWN"
        self.assertEqual(ldap_to_hpc_username(username, domain), "")

    def test_django_to_hpc_username_institute1(self):
        username = "user@" + settings.AUTH_LDAP_USERNAME_DOMAIN
        self.assertEqual(
            django_to_hpc_username(username), "user_" + settings.INSTITUTE_USERNAME_SUFFIX
        )

    def test_django_to_hpc_username_institute2(self):
        username = "user@" + settings.AUTH_LDAP2_USERNAME_DOMAIN
        self.assertEqual(
            django_to_hpc_username(username), "user_" + settings.INSTITUTE2_USERNAME_SUFFIX
        )

    def test_django_to_hpc_username_invalid_string(self):
        username = "user@A@B"
        self.assertEqual(django_to_hpc_username(username), "")

    def test_django_to_hpc_username_invalid_domain(self):
        username = "user@UNKNOWN"
        self.assertEqual(django_to_hpc_username(username), "")

    def test_convert_to_posix(self):
        name = "LeéèÄAöo"
        self.assertEqual(convert_to_posix(name), "LeeeAAoo")
