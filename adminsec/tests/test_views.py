import json
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from django.contrib.messages import get_messages
from django.urls import reverse

from adminsec.views import (
    django_to_hpc_username,
    convert_to_posix,
    generate_hpc_groupname,
    ldap_to_hpc_username,
)
from usersec.models import (
    HpcGroupCreateRequest,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_RETRACTED,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_APPROVED,
    HpcUser,
    HpcGroup,
)
from usersec.tests.factories import HpcGroupCreateRequestFactory, HpcUserCreateRequestFactory
from usersec.tests.test_views import TestViewBase


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
            self.assertEqual(
                response.context["comment_history"],
                request.get_comment_history(),
            )
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
        self.obj = HpcGroupCreateRequestFactory(requester=self.user, status=REQUEST_STATUS_ACTIVE)

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

    @override_settings(
        INSTITUTE_EMAIL_DOMAINS="charite.de",
        INSTITUTE_USERNAME_SUFFIX="c",
    )
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
            self.assertEqual(str(messages[0]), "Request approved and group and user created.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)

            hpcgroups = HpcGroup.objects.all()
            hpcusers = HpcUser.objects.all()

            self.assertEqual(hpcgroups.count(), 2)
            self.assertEqual(hpcusers.count(), 2)

            hpcuser = hpcusers.last()  # noqa: E1101
            hpcgroup = hpcgroups.last()  # noqa: E1101

            self.assertEqual(hpcuser.user, self.user)
            self.assertEqual(hpcuser.username, "user_" + settings.INSTITUTE_USERNAME_SUFFIX)
            self.assertEqual(hpcuser.primary_group, hpcgroup)
            self.assertEqual(hpcgroup.owner.user, self.user)
            self.assertEqual(hpcgroup.name, "ag_doe")


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
                data={"comment": "Denied!"},
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
            self.assertEqual(self.obj.comment, "Denied!")
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)


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
            self.assertEqual(
                response.context["comment_history"],
                request.get_comment_history(),
            )
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
            self.assertEqual(
                response.context["comment_history"],
                self.obj.get_comment_history(),
            )

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
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
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
            self.assertEqual(self.obj.editor, self.user_hpcadmin)
            self.assertEqual(self.obj.requester, self.user_owner)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Revision requested.")


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

        self.assertEqual(HpcUser.objects.count(), 1)

        with self.login(self.user_hpcadmin):
            response = self.client.post(
                reverse(
                    "adminsec:hpcusercreaterequest-approve",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 2)
            self.assertEqual(str(messages[0]), "Email sent to {}".format(self.obj.email))
            self.assertEqual(str(messages[1]), "Request approved and user created.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.status, REQUEST_STATUS_APPROVED)

            self.assertEqual(HpcUser.objects.count(), 2)
            user = HpcUser.objects.last()
            self.assertEqual(user.username, "new_user_" + settings.INSTITUTE_USERNAME_SUFFIX)
            self.assertIsNone(user.user)

            mock_get_ldap_username_domain_by_mail.assert_called_with(self.obj.email)
            mock_connect.assert_called_once()


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
                data={"comment": "Denied!"},
            )

            self.assertRedirects(
                response,
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": self.obj.uuid},
                ),
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Request successfully denied.")

            self.assertEqual(self.obj.status, REQUEST_STATUS_ACTIVE)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.comment, "Denied!")
            self.assertEqual(self.obj.status, REQUEST_STATUS_DENIED)


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

    def test_generate_hpc_groupname(self):
        name = "Doe"
        self.assertEqual(generate_hpc_groupname(name), "ag_doe")
