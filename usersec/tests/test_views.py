from django.contrib.messages import get_messages
from test_plus.test import TestCase
from django.urls import reverse

from usersec.models import HpcGroupCreateRequest
from usersec.tests.factories import (
    HpcUserFactory,
    HPCGROUPCREATEREQUESTFORM_DATA_VALID,
    HpcGroupCreateRequestFactory,
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
            response = self.client.post(reverse("usersec:orphan-user"), data=data)
            request = HpcGroupCreateRequest.objects.first()
            self.assertRedirects(
                response,
                reverse("usersec:pending-group-request", kwargs={"hpcgrouprequest": request.uuid}),
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
                response.context["form"].errors["resources_requested"][0], "This field is required."
            )


class TestPendingGroupRequestView(TestBase):
    """Tests for PendingGroupRequestView."""

    def test_get(self):
        request = HpcGroupCreateRequestFactory(requester=self.user)

        with self.login(self.user):
            response = self.client.get(
                reverse("usersec:pending-group-request", kwargs={"hpcgrouprequest": request.uuid})
            )

            self.assertEqual(response.status_code, 200)
