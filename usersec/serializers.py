"""DRF serializers for the usersec app."""

from typing import Optional

from rest_framework import serializers

from usersec.models import (
    HpcGroupCreateRequest,
    HpcGroupCreateRequestVersion,
    HpcGroupVersion,
    HpcProjectCreateRequest,
    HpcProjectCreateRequestVersion,
    HpcUser,
    HpcUserVersion,
)


class HpcObjectAbstractSerializer(serializers.Serializer):
    """Common base class for HPC object serializers."""

    uuid = serializers.CharField(read_only=True)
    date_created = serializers.DateTimeField(read_only=True)

    class Meta:
        fields = [
            "uuid",
            "date_created",
        ]


class HpcUserAbstractSerializer(HpcObjectAbstractSerializer):
    """Common base class for HPC user serializers."""

    primary_group = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    resources_requested = serializers.JSONField(read_only=True)
    resources_used = serializers.JSONField()
    status = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    uid = serializers.SerializerMethodField()
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

    def get_uid(self, obj) -> Optional[int]:
        return obj.user.uid

    def get_display_name(self, obj) -> Optional[str]:
        return obj.user.display_name

    class Meta:
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
        ]


class HpcUserSerializer(HpcUserAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcUser model."""

    current_version = serializers.IntegerField(read_only=True)

    class Meta:
        model = HpcUser
        fields = HpcUserAbstractSerializer.Meta.fields + [
            "current_version",
        ]


class HpcUserVersionSerializer(HpcUserAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcUserVersion model."""

    version = serializers.IntegerField(read_only=True)
    belongs_to = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    class Meta:
        model = HpcUserVersion
        fields = HpcUserAbstractSerializer.Meta.fields + [
            "version",
        ]


class HpcGroupAbstractSerializer(HpcObjectAbstractSerializer):
    """Common base class for HPC group serializers."""

    owner = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    delegate = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    resources_requested = serializers.JSONField(read_only=True)
    resources_used = serializers.JSONField()
    status = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    gid = serializers.IntegerField()
    name = serializers.CharField(read_only=True)
    folders = serializers.JSONField()
    expiration = serializers.DateTimeField(read_only=True)

    class Meta:
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


class HpcGroupSerializer(HpcGroupAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcGroup model."""

    current_version = serializers.IntegerField(read_only=True)

    class Meta:
        model = HpcUser
        fields = HpcGroupAbstractSerializer.Meta.fields + [
            "current_version",
        ]


class HpcGroupVersionSerializer(HpcGroupAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcGroupVersion model."""

    version = serializers.IntegerField(read_only=True)
    belongs_to = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    class Meta:
        model = HpcGroupVersion
        fields = HpcUserAbstractSerializer.Meta.fields + [
            "version",
        ]


class HpcProjectAbstractSerializer(HpcObjectAbstractSerializer):
    """Common base class for HPC project serializers."""

    group = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    delegate = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    resources_requested = serializers.JSONField(read_only=True)
    resources_used = serializers.JSONField()
    status = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    gid = serializers.IntegerField()
    name = serializers.CharField(read_only=True)
    folders = serializers.JSONField()
    expiration = serializers.DateTimeField(read_only=True)
    members = serializers.SlugRelatedField(slug_field="uuid", many=True, read_only=True)

    class Meta:
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


class HpcProjectSerializer(HpcProjectAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcProject model."""

    current_version = serializers.IntegerField(read_only=True)

    class Meta:
        model = HpcUser
        fields = HpcProjectAbstractSerializer.Meta.fields + [
            "current_version",
        ]


class HpcProjectVersionSerializer(HpcProjectAbstractSerializer, serializers.ModelSerializer):
    """Serializer for HpcProjectVersion model."""

    version = serializers.IntegerField(read_only=True)
    belongs_to = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    class Meta:
        model = HpcUserVersion
        fields = HpcProjectAbstractSerializer.Meta.fields + [
            "version",
        ]


class HpcRequestAbstractSerializer(HpcObjectAbstractSerializer):
    """Common base class for HPC request serializers."""

    status = serializers.CharField(read_only=True)
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


class HpcGroupCreateRequestAbstractSerializer(HpcGroupRequestAbstract):
    """Common base class for HPC group create request serializers."""

    resources_requested = serializers.JSONField(read_only=True)
    description = serializers.CharField(read_only=True)
    expiration = serializers.DateTimeField(read_only=True)
    folders = serializers.JSONField()
    name = serializers.CharField()

    class Meta:
        fields = HpcObjectAbstractSerializer.Meta.fields + [
            "resources_requested",
            "description",
            "expiration",
            "name",
            "folders",
        ]


class HpcGroupCreateRequestSerializer(
    HpcGroupCreateRequestAbstractSerializer, serializers.ModelSerializer
):
    """Serializer for HpcGroupCreateRequest model."""

    current_version = serializers.IntegerField(read_only=True)

    class Meta:
        model = HpcGroupCreateRequest
        fields = HpcGroupCreateRequestAbstractSerializer.Meta.fields + [
            "current_version",
        ]


class HpcGroupCreateRequestVersionSerializer(
    HpcGroupCreateRequestAbstractSerializer, serializers.ModelSerializer
):
    """Serializer for HpcGroupCreateRequestVersion model."""

    version = serializers.IntegerField(read_only=True)
    belongs_to = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    class Meta:
        model = HpcGroupCreateRequestVersion
        fields = HpcGroupCreateRequestAbstractSerializer.Meta.fields + [
            "version",
        ]


class HpcProjectRequestAbstract(HpcRequestAbstractSerializer):
    """Common base class for HPC group request serializers."""

    project = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    class Meta:
        fields = HpcRequestAbstractSerializer.Meta.fields + [
            "project",
        ]


class HpcProjectCreateRequestAbstractSerializer(HpcProjectRequestAbstract):
    """Common base class for HPC group create request serializers."""

    resources_requested = serializers.JSONField(read_only=True)
    description = serializers.CharField(read_only=True)
    expiration = serializers.DateTimeField(read_only=True)
    group = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    members = serializers.SlugRelatedField(slug_field="uuid", many=True, read_only=True)
    name_requested = serializers.CharField(read_only=True)
    name = serializers.CharField()
    folders = serializers.JSONField()

    class Meta:
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


class HpcProjectCreateRequestSerializer(
    HpcProjectCreateRequestAbstractSerializer, serializers.ModelSerializer
):
    """Serializer for HpcProjectCreateRequest model."""

    current_version = serializers.IntegerField(read_only=True)

    class Meta:
        model = HpcProjectCreateRequest
        fields = HpcProjectCreateRequestAbstractSerializer.Meta.fields + [
            "current_version",
        ]


class HpcProjectCreateRequestVersionSerializer(
    HpcProjectCreateRequestAbstractSerializer, serializers.ModelSerializer
):
    """Serializer for HpcProjectCreateRequestVersion model."""

    version = serializers.IntegerField(read_only=True)
    belongs_to = serializers.SlugRelatedField(slug_field="uuid", read_only=True)

    class Meta:
        model = HpcProjectCreateRequestVersion
        fields = HpcProjectCreateRequestAbstractSerializer.Meta.fields + [
            "version",
        ]
