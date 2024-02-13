"""Tests for the API views.

We mainly test the permissions here, the rest is mostly of smoke test
quality.
"""

from rest_framework.test import APIClient
from test_plus import TestCase

from usersec.tests.factories import HpcGroupFactory, HpcProjectFactory, HpcUserFactory


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
