"""DRF views for the adminsec app."""

import re

import attr
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAdminUser

from adminsec.constants import (
    RE_FOLDER,
    RE_NAME,
)
from adminsec.permissions_api import IsHpcAdminUser
from hpcaccess.utils.rest_framework import CursorPagination
from usersec.models import (
    HpcGroup,
    HpcGroupCreateRequest,
    HpcProject,
    HpcProjectCreateRequest,
    HpcUser,
)
from usersec.serializers import (
    HpcAccessStatusSerializer,
    HpcGroupCreateRequestSerializer,
    HpcGroupSerializer,
    HpcProjectCreateRequestSerializer,
    HpcProjectSerializer,
    HpcUserSerializer,
)


class HpcUserListPagination(CursorPagination):
    ordering = "username"


class HpcUserListApiView(ListAPIView):
    """API view for listing all users."""

    queryset = HpcUser.objects.all().order_by("username")
    serializer_class = HpcUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = HpcUserListPagination


class HpcUserRetrieveUpdateApiView(RetrieveUpdateAPIView):
    """API view for retrieving, updating and deleting a user."""

    queryset = HpcUser.objects.all()
    serializer_class = HpcUserSerializer
    permission_classes = [IsAdminUser]

    def get_object(self):
        """Return the object to be used in the view."""
        return get_object_or_404(HpcUser, uuid=self.kwargs["hpcuser"])


class HpcGroupListPagination(CursorPagination):
    ordering = "name"


class HpcGroupListApiView(ListAPIView):
    """API view for listing all groups."""

    queryset = HpcGroup.objects.all()
    serializer_class = HpcGroupSerializer
    permission_classes = [IsAdminUser]
    pagination_class = HpcGroupListPagination


class HpcGroupRetrieveUpdateApiView(RetrieveUpdateAPIView):
    """API view for retrieving, updating and deleting a user."""

    queryset = HpcGroup.objects.all()
    serializer_class = HpcGroupSerializer
    permission_classes = [IsAdminUser]

    def get_object(self):
        """Return the object to be used in the view."""
        return get_object_or_404(HpcGroup, uuid=self.kwargs["hpcgroup"])


class HpcProjectListPagination(CursorPagination):
    ordering = "name"


class HpcProjectListApiView(ListAPIView):
    """API view for listing all groups."""

    queryset = HpcProject.objects.all()
    serializer_class = HpcProjectSerializer
    permission_classes = [IsAdminUser]
    pagination_class = HpcProjectListPagination


class HpcProjectRetrieveUpdateApiView(RetrieveUpdateAPIView):
    """API view for retrieving, updating and deleting a user."""

    queryset = HpcProject.objects.all()
    serializer_class = HpcProjectSerializer
    permission_classes = [IsAdminUser]

    def get_object(self):
        """Return the object to be used in the view."""
        return get_object_or_404(HpcProject, uuid=self.kwargs["hpcproject"])


class HpcGroupCreateRequestRetrieveUpdateApiView(RetrieveUpdateAPIView):
    """API view for retrieving, updating and deleting a user."""

    queryset = HpcGroupCreateRequest.objects.all()
    serializer_class = HpcGroupCreateRequestSerializer
    permission_classes = [IsAdminUser | IsHpcAdminUser]

    def get_object(self):
        """Return the object to be used in the view."""
        return get_object_or_404(HpcGroupCreateRequest, uuid=self.kwargs["hpcgroupcreaterequest"])

    def perform_update(self, serializer):
        """Create a new object."""
        name = serializer.validated_data.get("name")
        folders = serializer.validated_data.get("folders")
        errors = {}

        if name is not None:
            if not re.match(RE_NAME, name):
                errors["name"] = (
                    "The group name must be lowercase, alphanumeric including hyphens (-), "
                    "not starting with a number or a hyphen or ending with a hyphen. "
                    f"(regex: {RE_NAME})"
                )

            elif HpcGroup.objects.filter(name=name).exists():
                errors["name"] = f"Group with name `{name}` already exists."

        for fkey, folder in folders.items():
            if folder is not None:
                m = re.match(RE_FOLDER, folder)
                if not m:
                    errors[fkey] = (
                        "The path must be a valid UNIX path starting with a slash, "
                        "only alphanumeric and hpyhen and underscore are allowed and "
                        "the last folder name must follow the group name rules. "
                        f"(regex: {RE_FOLDER})"
                    )

                elif HpcGroup.objects.filter(folders__contains={fkey: folder}).exists():
                    errors[fkey] = f"Folder with path '{folder}' already exists."

                elif not name == m.group("name"):
                    errors[fkey] = (
                        "The last folder name the be same as the group name. "
                        f"(group name: {name})"
                    )

        if errors:
            raise ValidationError(errors)

        super().perform_update(serializer)


class HpcProjectCreateRequestRetrieveUpdateApiView(RetrieveUpdateAPIView):
    """API view for retrieving, updating and deleting a user."""

    queryset = HpcProjectCreateRequest.objects.all()
    serializer_class = HpcProjectCreateRequestSerializer
    permission_classes = [IsAdminUser | IsHpcAdminUser]

    def get_object(self):
        """Return the object to be used in the view."""
        return get_object_or_404(
            HpcProjectCreateRequest, uuid=self.kwargs["hpcprojectcreaterequest"]
        )

    def perform_update(self, serializer):
        """Create a new object."""
        name = serializer.validated_data.get("name")
        folders = serializer.validated_data.get("folders")
        errors = {}

        if name is not None:
            if not re.match(RE_NAME, name):
                errors["name"] = (
                    "The project name must be lowercase, alphanumeric including hyphens (-), "
                    "not starting with a number or a hyphen or ending with a hyphen. "
                    f"(regex: {RE_NAME})"
                )

            elif HpcProject.objects.filter(name=name).exists():
                errors["name"] = f"Project with name `{name}` already exists."

        for fkey, folder in folders.items():
            if folder is not None:
                m = re.match(RE_FOLDER, folder)
                if not m:
                    errors[fkey] = (
                        "The path must be a valid UNIX path starting with a slash, "
                        "only alphanumeric and hpyhen and underscore are allowed and "
                        "the last folder name must follow the project name rules. "
                        f"(regex: {RE_FOLDER})"
                    )

                elif HpcProject.objects.filter(folders__contains={fkey: folder}).exists():
                    errors[fkey] = f"Folder with path '{folder}' already exists."

                elif not name == m.group("name"):
                    errors[fkey] = (
                        "The last folder name the be same as the project name. "
                        f"(project name: {name})"
                    )

        if errors:
            raise ValidationError(errors)

        super().perform_update(serializer)


@attr.s(frozen=True)
class HpcAccessStatus:
    """Class to hold the status of the HPC access system."""

    hpc_users: dict = attr.ib()
    hpc_groups: dict = attr.ib()
    hpc_projects: dict = attr.ib()


class HpcAccessStatusApiView(RetrieveAPIView):
    """API view for listing all users."""

    serializer_class = HpcAccessStatusSerializer

    def get_object(self):
        """Return the object to be used in the view."""
        return HpcAccessStatus(
            hpc_users=HpcUser.objects.all(),
            hpc_groups=HpcGroup.objects.all(),
            hpc_projects=HpcProject.objects.all(),
        )
