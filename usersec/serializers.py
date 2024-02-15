"""DRF serializers for the usersec app."""

from typing import Optional

from rest_framework import serializers

from usersec.models import HpcGroupVersion, HpcUser, HpcUserVersion


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
    full_name = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    home_directory = serializers.CharField()
    login_shell = serializers.CharField()

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

    class Meta:
        fields = HpcObjectAbstractSerializer.Meta.fields + [
            "full_name",
            "first_name",
            "last_name",
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
    folder = serializers.CharField()
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
            "folder",
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
    folder = serializers.CharField()
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
            "folder",
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
