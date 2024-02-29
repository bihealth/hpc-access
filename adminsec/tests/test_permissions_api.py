from django.test import RequestFactory
from test_plus import TestCase

from adminsec.permissions_api import IsHpcAdminUser


class TestHpcUserListApiView(TestCase):
    """Test the HpcUserListApiView"""

    def setUp(self):
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
        self.factory = RequestFactory()

    def test_get_allowed(self):
        request = self.factory.get("/")

        for user in [self.user_hpcadmin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertTrue(permission)

    def test_get_denied(self):
        request = self.factory.get("/")

        for user in [self.user_user, self.user_staff, self.user_admin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertFalse(permission)

    def test_post_allowed(self):
        request = self.factory.post("/")

        for user in [self.user_hpcadmin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertTrue(permission)

    def test_post_denied(self):
        request = self.factory.post("/")

        for user in [self.user_user, self.user_staff, self.user_admin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertFalse(permission)

    def test_patch_allowed(self):
        request = self.factory.patch("/")

        for user in [self.user_hpcadmin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertTrue(permission)

    def test_patch_denied(self):
        request = self.factory.patch("/")

        for user in [self.user_user, self.user_staff, self.user_admin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertFalse(permission)

    def test_put_allowed(self):
        request = self.factory.put("/")

        for user in [self.user_hpcadmin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertTrue(permission)

    def test_put_denied(self):
        request = self.factory.put("/")

        for user in [self.user_user, self.user_staff, self.user_admin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertFalse(permission)

    def test_delete_allowed(self):
        request = self.factory.delete("/")

        for user in [self.user_hpcadmin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertTrue(permission)

    def test_delete_denied(self):
        request = self.factory.delete("/")

        for user in [self.user_user, self.user_staff, self.user_admin]:
            request.user = user
            permission_check = IsHpcAdminUser()
            permission = permission_check.has_permission(request, None)
            self.assertFalse(permission)
