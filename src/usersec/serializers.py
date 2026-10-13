"""DRF serializers for the usersec app."""

from typing import Optional

from django.db import models
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from usersec.models import (
    HpcGroup,
    HpcGroupCreateRequest,
    HpcProject,
    HpcProjectCreateRequest,
    HpcUser,
)

HPC_ALUMNI_GROUP = "hpc-alumnis"


class Status(models.TextChoices):
    """Status of an HPC user, group, or project."""

    INITIAL = "INITIAL"
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    EXPIRED = "EXPIRED"


class ResourceDataSerializer(serializers.Serializer):
    """Resource request/usage for a group or project."""

    tier1_work = serializers.FloatField(default=0.0)
    tier1_scratch = serializers.FloatField(default=0.0)
    tier2_mirrored = serializers.FloatField(default=0.0)
    tier2_unmirrored = serializers.FloatField(default=0.0)


class ResourceDataUserSerializer(serializers.Serializer):
    """Resource request/usage for a user."""

    tier1_home = serializers.FloatField(default=0.0)


class GroupFoldersSerializer(serializers.Serializer):
    """Folders for a group or project."""

    tier1_work = serializers.CharField()
    tier1_scratch = serializers.CharField()
    tier2_mirrored = serializers.CharField()
    tier2_unmirrored = serializers.CharField()


@extend_schema_field(ResourceDataUserSerializer)
class ResourceDataUserJSONField(serializers.JSONField):
    """JSON field annotated as ResourceDataUser for schema generation."""


@extend_schema_field(ResourceDataSerializer)
class ResourceDataJSONField(serializers.JSONField):
    """JSON field annotated as ResourceData for schema generation."""


@extend_schema_field(GroupFoldersSerializer)
class GroupFoldersJSONField(serializers.JSONField):
    """JSON field annotated as GroupFolders for schema generation."""


class HpcObjectAbstractSerializer(serializers.Serializer):
    """Common base class for HPC object serializers."""

    uuid = serializers.CharField(read_only=True)
    date_created = serializers.DateTimeField(read_only=True)

    class Meta:
        fields = [
            "uuid",
            "date_created",
        ]


class HpcUserSerializer(HpcObjectAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcUser model."""

    primary_group = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    resources_requested = ResourceDataUserJSONField(read_only=True)
    resources_used = ResourceDataUserJSONField()

    status = serializers.ChoiceField(choices=Status.choices, read_only=True)
    description = serializers.CharField(
        read_only=True,
        required=False,
        allow_null=True,
    )
    uid = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    expiration = serializers.DateTimeField(read_only=True)
    email = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    home_directory = serializers.CharField()
    login_shell = serializers.CharField()
    removed = serializers.BooleanField(
        read_only=True,
        required=False,
        allow_null=True,
    )

    def get_email(self, obj) -> Optional[str]:
        return obj.user.email

    def get_full_name(self, obj) -> str:
        return obj.user.name

    def get_last_name(self, obj) -> Optional[str]:
        return obj.user.last_name

    def get_first_name(self, obj) -> Optional[str]:
        return obj.user.first_name

    def get_phone_number(self, obj) -> Optional[str]:
        return obj.user.phone

    def get_display_name(self, obj) -> Optional[str]:
        return obj.user.display_name

    class Meta:
        model = HpcUser
        fields = HpcObjectAbstractSerializer.Meta.fields + [
            "email",
            "full_name",
            "first_name",
            "last_name",
            "display_name",
            "phone_number",
            "primary_group",
            "resources_requested",
            "resources_used",
            "status",
            "description",
            "uid",
            "username",
            "expiration",
            "home_directory",
            "login_shell",
            "removed",
        ]


class HpcGroupSerializer(HpcObjectAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcGroup model."""

    owner = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    delegate = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    resources_requested = ResourceDataJSONField(read_only=True)
    resources_used = ResourceDataJSONField()

    status = serializers.ChoiceField(choices=Status.choices, read_only=True)
    description = serializers.CharField(read_only=True)
    gid = serializers.IntegerField()
    name = serializers.CharField(read_only=True)
    folders = GroupFoldersJSONField()
    expiration = serializers.DateTimeField(read_only=True)

    class Meta:
        model = HpcGroup
        fields = HpcObjectAbstractSerializer.Meta.fields + [
            "owner",
            "delegate",
            "resources_requested",
            "resources_used",
            "status",
            "description",
            "gid",
            "name",
            "folders",
            "expiration",
        ]


class HpcProjectSerializer(HpcObjectAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcProject model."""

    group = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    delegate = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    resources_requested = ResourceDataJSONField(read_only=True)
    resources_used = ResourceDataJSONField()

    status = serializers.ChoiceField(choices=Status.choices, read_only=True)
    description = serializers.CharField(read_only=True)
    gid = serializers.IntegerField()
    name = serializers.CharField(read_only=True)
    folders = GroupFoldersJSONField()

    expiration = serializers.DateTimeField(read_only=True)
    members = serializers.SlugRelatedField(slug_field="uuid", many=True, read_only=True)

    class Meta:
        model = HpcProject
        fields = HpcObjectAbstractSerializer.Meta.fields + [
            "group",
            "delegate",
            "resources_requested",
            "resources_used",
            "status",
            "description",
            "gid",
            "name",
            "folders",
            "expiration",
            "members",
        ]


class HpcRequestAbstractSerializer(HpcObjectAbstractSerializer):
    """Common base class for HPC request serializers."""

    status = serializers.ChoiceField(choices=Status.choices, read_only=True)
    requester = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    comment = serializers.CharField(read_only=True)

    class Meta:
        fields = HpcObjectAbstractSerializer.Meta.fields + [
            "status",
            "requester",
            "comment",
        ]


class HpcGroupRequestAbstract(HpcRequestAbstractSerializer):
    """Common base class for HPC group request serializers."""

    group = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    class Meta:
        fields = HpcRequestAbstractSerializer.Meta.fields + [
            "group",
        ]


class HpcGroupCreateRequestSerializer(HpcGroupRequestAbstract, serializers.ModelSerializer):
    """Serializer for HpcGroupCreateRequest model."""

    resources_requested = ResourceDataJSONField(read_only=True)
    description = serializers.CharField(read_only=True)
    expiration = serializers.DateTimeField(read_only=True)
    folders = GroupFoldersJSONField()
    name = serializers.CharField()

    class Meta:
        model = HpcGroupCreateRequest
        fields = HpcObjectAbstractSerializer.Meta.fields + [
            "resources_requested",
            "description",
            "expiration",
            "name",
            "folders",
        ]


class HpcProjectRequestAbstract(HpcRequestAbstractSerializer):
    """Common base class for HPC group request serializers."""

    project = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    class Meta:
        fields = HpcRequestAbstractSerializer.Meta.fields + [
            "project",
        ]


class HpcProjectCreateRequestSerializer(HpcProjectRequestAbstract, serializers.ModelSerializer):
    """Serializer for HpcProjectCreateRequest model."""

    resources_requested = ResourceDataJSONField(read_only=True)
    description = serializers.CharField(read_only=True)
    expiration = serializers.DateTimeField(read_only=True)
    group = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    members = serializers.SlugRelatedField(slug_field="uuid", many=True, read_only=True)
    name_requested = serializers.CharField(read_only=True)
    name = serializers.CharField()

    folders = GroupFoldersJSONField()

    class Meta:
        model = HpcProjectCreateRequest
        fields = HpcObjectAbstractSerializer.Meta.fields + [
            "resources_requested",
            "description",
            "expiration",
            "group",
            "members",
            "name",
            "name_requested",
            "folders",
        ]


class HpcUserLookupSerializer(serializers.ModelSerializer):
    """Serializer for HpcUser model for lookup purposes."""

    primary_group = serializers.SlugRelatedField(slug_field="name", read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.user.name

    class Meta:
        model = HpcUser
        fields = [
            "id",
            "username",
            "primary_group",
            "full_name",
        ]
