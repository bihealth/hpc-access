"""Tests for the API views.

We mainly test the permissions here, the rest is mostly of smoke test
quality.
"""

from rest_framework.test import APIClient
from test_plus import TestCase

from usersec.models import REQUEST_STATUS_ACTIVE
from usersec.tests.factories import (
    HpcGroupCreateRequestFactory,
    HpcGroupFactory,
    HpcProjectFactory,
    HpcUserFactory,
)


class ApiTestCase(TestCase):
    """Base class for API test cases."""

    client_class = APIClient

    def setUp(self):
        super().setUp()
        # Create usersec.models records.
        self.hpcuser_user = HpcUserFactory()
        self.hpcuser_group = HpcGroupFactory()
        self.hpcuser_project = HpcProjectFactory()
        # Create Django users.
        self.user_user = self.make_user("user")
        self.user_staff = self.make_user("staff")
        self.user_staff.is_staff = True
        self.user_staff.save()
        self.user_admin = self.make_user("admin")
        self.user_admin.is_staff = True
        self.user_admin.is_superuser = True
        self.user_admin.save()
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()
        # Connect user to HpcUser.
        self.user_user.name = "User Name"
        self.user_user.save()
        self.hpcuser_user.user = self.user_user
        self.hpcuser_user.save()
        # Create HpcGroupCreateRequest.
        self.hpcgroupcreaterequest = HpcGroupCreateRequestFactory(
            requester=self.user_user, status=REQUEST_STATUS_ACTIVE, group_name="groupname"
        )


class TestHpcUserListApiView(ApiTestCase):
    """Tests for the HpcUserListApiView."""

    def test_get_succeed(self):
        """Test the GET method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.get("adminsec:api-hpcuser-list")
                self.response_200()

    def test_get_fail(self):
        """Test the GET method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.get("adminsec:api-hpcuser-list")
                self.response_403()

    def test_post_fail(self):
        """No user can POST."""
        for user in [self.user_staff, self.user_admin, self.user_user]:
            with self.login(user):
                self.post("adminsec:api-hpcuser-list", data={})
                if user.is_staff:
                    self.response_405()
                else:
                    self.response_403()


class TestHpcUserRetrieveUpdateApiView(ApiTestCase):
    """Tests for the HpcUserRetrieveUpdateApiView."""

    def test_get_succeed(self):
        """Test the GET method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.get("adminsec:api-hpcuser-retrieveupdate", hpcuser=self.hpcuser_user.uuid)
                self.response_200()

    def test_get_fail(self):
        """Test the GET method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.get("adminsec:api-hpcuser-retrieveupdate", hpcuser=self.hpcuser_user.uuid)
                self.response_403()

    def test_patch_succeed(self):
        """Test the PATCH method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.patch(
                    "adminsec:api-hpcuser-retrieveupdate", hpcuser=self.hpcuser_user.uuid, data={}
                )
                self.response_200()

    def test_patch_fail(self):
        """Test the PATCH method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.patch(
                    "adminsec:api-hpcuser-retrieveupdate", hpcuser=self.hpcuser_user.uuid, data={}
                )
                self.response_403()

    def test_delete_fail(self):
        """No user can DELETE."""
        for user in [self.user_staff, self.user_admin, self.user_user]:
            with self.login(user):
                self.delete("adminsec:api-hpcuser-retrieveupdate", hpcuser=self.hpcuser_user.uuid)
                if user.is_staff:
                    self.response_405()
                else:
                    self.response_403()


class TestHpcGroupListApiView(ApiTestCase):
    """Tests for the HpcGroupListApiView."""

    def test_get_succeed(self):
        """Test the GET method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.get("adminsec:api-hpcgroup-list")
                self.response_200()

    def test_get_fail(self):
        """Test the GET method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.get("adminsec:api-hpcgroup-list")
                self.response_403()

    def test_post_fail(self):
        """No user can POST."""
        for user in [self.user_staff, self.user_admin, self.user_user]:
            with self.login(user):
                self.post("adminsec:api-hpcgroup-list", data={})
                if user.is_staff:
                    self.response_405()
                else:
                    self.response_403()


class TestHpcGroupRetrieveUpdateApiView(ApiTestCase):
    """Tests for the HpcGroupRetrieveUpdateApiView."""

    def test_get_succeed(self):
        """Test the GET method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.get("adminsec:api-hpcgroup-retrieveupdate", hpcgroup=self.hpcuser_group.uuid)
                self.response_200()

    def test_get_fail(self):
        """Test the GET method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.get("adminsec:api-hpcgroup-retrieveupdate", hpcgroup=self.hpcuser_group.uuid)
                self.response_403()

    def test_patch_succeed(self):
        """Test the PATCH method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.patch(
                    "adminsec:api-hpcgroup-retrieveupdate",
                    hpcgroup=self.hpcuser_group.uuid,
                    data={},
                )
                self.response_200()

    def test_patch_fail(self):
        """Test the PATCH method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.patch(
                    "adminsec:api-hpcgroup-retrieveupdate",
                    hpcgroup=self.hpcuser_group.uuid,
                    data={},
                )
                self.response_403()

    def test_delete_fail(self):
        """No user can DELETE."""
        for user in [self.user_staff, self.user_admin, self.user_user]:
            with self.login(user):
                self.delete(
                    "adminsec:api-hpcgroup-retrieveupdate", hpcgroup=self.hpcuser_group.uuid
                )
                if user.is_staff:
                    self.response_405()
                else:
                    self.response_403()


class TestHpcProjectListApiView(ApiTestCase):
    """Tests for the HpcProjectListApiView."""

    def test_get_succeed(self):
        """Test the GET method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.get("adminsec:api-hpcproject-list")
                self.response_200()

    def test_get_fail(self):
        """Test the GET method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.get("adminsec:api-hpcproject-list")
                self.response_403()

    def test_post_fail(self):
        """No user can POST."""
        for user in [self.user_staff, self.user_admin, self.user_user]:
            with self.login(user):
                self.post("adminsec:api-hpcproject-list", data={})
                if user.is_staff:
                    self.response_405()
                else:
                    self.response_403()


class TestHpcProjectRetrieveUpdateApiView(ApiTestCase):
    """Tests for the HpcProjectRetrieveUpdateApiView."""

    def test_get_succeed(self):
        """Test the GET method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.get(
                    "adminsec:api-hpcproject-retrieveupdate", hpcproject=self.hpcuser_project.uuid
                )
                self.response_200()

    def test_get_fail(self):
        """Test the GET method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.get(
                    "adminsec:api-hpcproject-retrieveupdate", hpcproject=self.hpcuser_project.uuid
                )
                self.response_403()

    def test_patch_succeed(self):
        """Test the PATCH method (staff users can do)."""
        for user in [self.user_staff, self.user_admin]:
            with self.login(user):
                self.patch(
                    "adminsec:api-hpcproject-retrieveupdate",
                    hpcproject=self.hpcuser_project.uuid,
                    data={},
                )
                self.response_200()

    def test_patch_fail(self):
        """Test the PATCH method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.patch(
                    "adminsec:api-hpcproject-retrieveupdate",
                    hpcproject=self.hpcuser_project.uuid,
                    data={},
                )
                self.response_403()

    def test_delete_fail(self):
        """No user can DELETE."""
        for user in [self.user_staff, self.user_admin, self.user_user]:
            with self.login(user):
                self.delete(
                    "adminsec:api-hpcproject-retrieveupdate", hpcproject=self.hpcuser_project.uuid
                )
                if user.is_staff:
                    self.response_405()
                else:
                    self.response_403()


class TestHpcGroupCreateRequestRetrieveUpdateApiView(ApiTestCase):
    """Tests for the HpcGroupCreateRequestRetrieveUpdateApiView."""

    def test_get_succeed(self):
        """Test the GET method (staff users can do)."""
        for user in [self.user_staff, self.user_admin, self.user_hpcadmin]:
            with self.login(user):
                self.get(
                    "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                    hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                )
                self.response_200()

    def test_get_fail(self):
        """Test the GET method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.get(
                    "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                    hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                )
                self.response_403()

    def test_patch_succeed(self):
        """Test the PATCH method (staff users can do)."""
        for user in [self.user_staff, self.user_admin, self.user_hpcadmin]:
            with self.login(user):
                self.patch(
                    "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                    hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                    data={"group_name": "hpc-ag-newname", "folder": "/newfolder"},
                )
                self.response_200()

    def test_patch_fail_403(self):
        """Test the PATCH method (non-staff cannot do)."""
        for user in [self.user_user]:
            with self.login(user):
                self.patch(
                    "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                    hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                    data={"group_name": "hpc-ag-newname", "folder": "/newfolder"},
                )
                self.response_403()

    def test_patch_fail_400_group_name_regex(self):
        """Test the PATCH method (non-staff cannot do)."""
        with self.login(self.user_hpcadmin):
            self.patch(
                "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                data={"group_name": "newname", "folder": "/newfolder"},
            )
            self.response_400()
            self.assertEqual(
                self.last_response.json(),
                {
                    "group_name": (
                        "The group name must start with `hpc-ag-`, be lowercase, "
                        "alphanumeric including hyphens (-), not starting with a number "
                        "or a hyphen or ending with a hyphen. (regex: "
                        "^hpc-ag-[a-z][a-z0-9-]*[a-z0-9]$)"
                    )
                },
            )

    def test_patch_fail_400_group_name_duplicate(self):
        """Test the PATCH method (non-staff cannot do)."""
        self.hpcuser_group.name = "hpc-ag-newname"
        self.hpcuser_group.save()
        with self.login(self.user_hpcadmin):
            self.patch(
                "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                data={"group_name": "hpc-ag-newname", "folder": "/newfolder"},
            )
            self.response_400()
            self.assertEqual(
                self.last_response.json(),
                {"group_name": "Group with name `hpc-ag-newname` already exists."},
            )

    def test_patch_fail_400_folder_regex(self):
        """Test the PATCH method (non-staff cannot do)."""
        with self.login(self.user_hpcadmin):
            self.patch(
                "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                data={"group_name": "hpc-ag-newname", "folder": "2newfolder"},
            )
            self.response_400()
            self.assertEqual(
                self.last_response.json(),
                {
                    "folder": (
                        "The path must be a valid UNIX path starting with a slash, only "
                        "alphanumeric and hpyhen and underscore are allowed and the last "
                        "folder name must follow the group name rules. (regex: "
                        "^(/[a-zA-Z0-9-_]*)+[a-z][a-z0-9-]*[a-z0-9]$)"
                    )
                },
            )

    def test_patch_fail_400_folder_duplicate(self):
        """Test the PATCH method (non-staff cannot do)."""
        self.hpcuser_group.folder = "/newfolder"
        self.hpcuser_group.save()
        with self.login(self.user_hpcadmin):
            self.patch(
                "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                data={"group_name": "hpc-ag-newname", "folder": "/newfolder"},
            )
            self.response_400()
            self.assertEqual(
                self.last_response.json(),
                {"folder": "Folder with path '/newfolder' already exists."},
            )

    def test_delete_fail(self):
        """No user can DELETE."""
        for user in [self.user_staff, self.user_admin, self.user_user, self.user_hpcadmin]:
            with self.login(user):
                self.delete(
                    "adminsec:api-hpcgroupcreaterequest-retrieveupdate",
                    hpcgroupcreaterequest=self.hpcgroupcreaterequest.uuid,
                )
                if user.is_staff or user.is_hpcadmin:
                    self.response_405()
                else:
                    self.response_403()
