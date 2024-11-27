from django.db.models import Q
from rest_framework.generics import ListAPIView

from usersec.models import HpcUser
from usersec.serializers import HpcUserLookupSerializer


class HpcUserLookupApiView(ListAPIView):
    """API view for retrieving, updating and deleting a user."""

    queryset = HpcUser.objects.all()
    serializer_class = HpcUserLookupSerializer
    # permission_classes = []

    def paginate_queryset(self, _queryset):
        # Don't paginate the results
        return None

    def filter_queryset(self, queryset=None):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(
            Q(username__icontains=self.request.query_params.get("q", ""))
            | Q(user__name__icontains=self.request.query_params.get("q", ""))
        )
