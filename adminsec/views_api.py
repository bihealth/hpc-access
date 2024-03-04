"""DRF views for the adminsec app."""

import re

from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAdminUser

from adminsec.constants import (
    POSIX_AG_PREFIX,
    POSIX_PROJECT_PREFIX,
    RE_FOLDER_CHECK,
    RE_GROUP_NAME_CHECK,
    RE_PROJECT_NAME_CHECK,
)
from adminsec.permissions_api import IsHpcAdminUser
from usersec.models import (
    HpcGroup,
    HpcGroupCreateRequest,
    HpcProject,
    HpcProjectCreateRequest,
    HpcUser,
)
from usersec.serializers import (
    HpcGroupCreateRequestSerializer,
    HpcGroupSerializer,
    HpcProjectCreateRequestSerializer,
    HpcProjectSerializer,
    HpcUserSerializer,
)


class HpcUserListApiView(ListAPIView):
    """API view for listing all users."""

    queryset = HpcUser.objects.all()
    serializer_class = HpcUserSerializer
    permission_classes = [IsAdminUser]


class HpcUserRetrieveUpdateApiView(RetrieveUpdateAPIView):
    """API view for retrieving, updating and deleting a user."""

    queryset = HpcUser.objects.all()
    serializer_class = HpcUserSerializer
    permission_classes = [IsAdminUser]

    def get_object(self):
        """Return the object to be used in the view."""
        return get_object_or_404(HpcUser, uuid=self.kwargs["hpcuser"])


class HpcGroupListApiView(ListAPIView):
    """API view for listing all groups."""

    queryset = HpcGroup.objects.all()
    serializer_class = HpcGroupSerializer
    permission_classes = [IsAdminUser]


class HpcGroupRetrieveUpdateApiView(RetrieveUpdateAPIView):
    """API view for retrieving, updating and deleting a user."""

    queryset = HpcGroup.objects.all()
    serializer_class = HpcGroupSerializer
    permission_classes = [IsAdminUser]

    def get_object(self):
        """Return the object to be used in the view."""
        return get_object_or_404(HpcGroup, uuid=self.kwargs["hpcgroup"])


class HpcProjectListApiView(ListAPIView):
    """API view for listing all groups."""

    queryset = HpcProject.objects.all()
    serializer_class = HpcProjectSerializer
    permission_classes = [IsAdminUser]


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
        folder = serializer.validated_data.get("folder")

        if name is not None:
            if not re.match(RE_GROUP_NAME_CHECK, name):
                raise ValidationError(
                    {
                        "name": (
                            f"The group name must start with `{POSIX_AG_PREFIX}`, be lowercase, "
                            "alphanumeric including hyphens (-), not starting with a number or "
                            f"a hyphen or ending with a hyphen. (regex: {RE_GROUP_NAME_CHECK})"
                        )
                    }
                )

            if HpcGroup.objects.filter(name=name).exists():
                raise ValidationError({"name": f"Group with name `{name}` already exists."})

        if folder is not None:
            if not re.match(RE_FOLDER_CHECK, folder):
                raise ValidationError(
                    {
                        "folder": (
                            "The path must be a valid UNIX path starting with a slash, "
                            "only alphanumeric and hpyhen and underscore are allowed and "
                            "the last folder name must follow the group name rules. "
                            f"(regex: {RE_FOLDER_CHECK})"
                        )
                    }
                )

            if HpcGroup.objects.filter(folder=folder).exists():
                raise ValidationError({"folder": f"Folder with path '{folder}' already exists."})

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
        folder = serializer.validated_data.get("folder")

        if name is not None:
            if not re.match(RE_PROJECT_NAME_CHECK, name):
                raise ValidationError(
                    {
                        "name": (
                            f"The project name must start with `{POSIX_PROJECT_PREFIX}`, be lowercase, "
                            "alphanumeric including hyphens (-), not starting with a number or "
                            f"a hyphen or ending with a hyphen. (regex: {RE_PROJECT_NAME_CHECK})"
                        )
                    }
                )

            if HpcProject.objects.filter(name=name).exists():
                raise ValidationError({"name": f"Project with name `{name}` already exists."})

        if folder is not None:
            if not re.match(RE_FOLDER_CHECK, folder):
                raise ValidationError(
                    {
                        "folder": (
                            "The path must be a valid UNIX path starting with a slash, "
                            "only alphanumeric and hpyhen and underscore are allowed and "
                            "the last folder name must follow the project name rules. "
                            f"(regex: {RE_FOLDER_CHECK})"
                        )
                    }
                )

            if HpcProject.objects.filter(folder=folder).exists():
                raise ValidationError({"folder": f"Folder with path '{folder}' already exists."})

        super().perform_update(serializer)
