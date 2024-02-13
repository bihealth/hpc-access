"""DRF views for the adminsec app."""

from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAdminUser

from usersec.models import HpcGroup, HpcProject, HpcUser
from usersec.serializers import (
    HpcGroupSerializer,
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
