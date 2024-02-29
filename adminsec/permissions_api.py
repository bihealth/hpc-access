from rest_framework.permissions import BasePermission


class IsHpcAdminUser(BasePermission):
    """Custom permission to allow only HPC admin users to access the view."""

    def has_permission(self, request, view):
        """Return True if the user is an HPC admin user."""
        return request.user.is_hpcadmin
