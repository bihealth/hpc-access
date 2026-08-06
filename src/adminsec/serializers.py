"""DRF serializers for the adminsec app."""

from rest_framework import serializers

from usersec.serializers import HpcGroupSerializer, HpcProjectSerializer, HpcUserSerializer


class HpcaccessStateSerializer(serializers.Serializer):
    """Cluster status (users, groups, and projects)."""

    hpc_users = serializers.DictField(child=HpcUserSerializer())
    hpc_groups = serializers.DictField(child=HpcGroupSerializer())
    hpc_projects = serializers.DictField(child=HpcProjectSerializer())
