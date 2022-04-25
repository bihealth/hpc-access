import uuid as uuid_object

from django.db import models, transaction
from django.urls import reverse
from factory.django import get_model

from hpcaccess.users.models import User

APP_NAME = "usersec"

#: Object is initialized.
OBJECT_STATUS_INITIAL = "INITIAL"

#: Object is set active.
OBJECT_STATUS_ACTIVE = "ACTIVE"

#: Object marked as deleted.
OBJECT_STATUS_DELETED = "DELETED"

#: Object expired.
OBJECT_STATUS_EXPIRED = "EXPIRED"

#: Group, project and user statuses.
OBJECT_STATUS_CHOICES = [
    (OBJECT_STATUS_INITIAL, OBJECT_STATUS_INITIAL),
    (OBJECT_STATUS_ACTIVE, OBJECT_STATUS_ACTIVE),
    (OBJECT_STATUS_DELETED, OBJECT_STATUS_DELETED),
    (OBJECT_STATUS_EXPIRED, OBJECT_STATUS_EXPIRED),
]

#: Request has been created.
REQUEST_STATUS_INITIAL = "INITIAL"

#: Request is set active waiting for approval.
REQUEST_STATUS_ACTIVE = "ACTIVE"

#: Request needs a revision.
REQUEST_STATUS_REVISION = "REVISION"

#: Request revision submitted.
REQUEST_STATUS_REVISED = "REVISED"

#: Request was approved.
REQUEST_STATUS_APPROVED = "APPROVED"

#: Request was denied.
REQUEST_STATUS_DENIED = "DENIED"

#: Request retracted by requester.
REQUEST_STATUS_RETRACTED = "RETRACTED"

#: Request statuses.
REQUEST_STATUS_CHOICES = [
    (REQUEST_STATUS_INITIAL, REQUEST_STATUS_INITIAL),
    (REQUEST_STATUS_ACTIVE, REQUEST_STATUS_ACTIVE),
    (REQUEST_STATUS_REVISION, REQUEST_STATUS_REVISION),
    (REQUEST_STATUS_REVISED, REQUEST_STATUS_REVISED),
    (REQUEST_STATUS_APPROVED, REQUEST_STATUS_APPROVED),
    (REQUEST_STATUS_DENIED, REQUEST_STATUS_DENIED),
    (REQUEST_STATUS_RETRACTED, REQUEST_STATUS_RETRACTED),
]


# ------------------------------------------------------------------------------
# Mixins
# ------------------------------------------------------------------------------


class VersionManager(models.Manager):
    """Functions for creating, updating and deleting objects with version objects."""

    def version_model(self, **kwargs):
        return get_model(APP_NAME, f"{self.model.__name__}Version")(**kwargs)

    @transaction.atomic
    def create_with_version(self, **kwargs):
        """
        Create a new object with the given kwargs, saving it to the database
        and returning the created object.
        """

        # Allow passing version for testing reasons mainly
        version = kwargs.pop("current_version", 1)

        obj = self.model(**kwargs, current_version=version)
        obj.save()

        version_obj = self.version_model(**kwargs, version=version, belongs_to=obj)
        version_obj.save()

        # TODO: look up when version passed and not 1 if the version history is ok

        return obj

    # def update_with_version(self, **kwargs):
    #     # TODO: update all from queryset with the given values
    #     pass
    #
    # def delete_with_version(self):
    #     # TODO delete all from queryset
    #     pass


class VersionRequestManager(VersionManager):
    """Custom manager for requests."""

    def active(self, **kwargs):
        kwargs.update({"status__in": (REQUEST_STATUS_ACTIVE, REQUEST_STATUS_REVISED)})
        return super().get_queryset().filter(**kwargs)


class VersionManagerMixin:
    """Mixin for version functionality."""

    def get_latest_version(self):
        max_obj = None

        if not self.current_version:
            return max_obj

        for obj in self.version_history.filter(version__gte=self.current_version):
            if max_obj is None or max_obj.version > obj.version:
                max_obj = obj

        return max_obj

    @transaction.atomic
    def save_with_version(self):
        latest = self.get_latest_version()
        self.current_version = (latest.version + 1) if latest else 1
        self.save()

        # Create version object
        version_obj = get_model(APP_NAME, f"{self.__class__.__name__}Version")()
        version_obj.version = self.current_version
        version_obj.belongs_to = self

        for field in self._meta.fields:
            if field.name in ("id", "uuid", "current_version", "date_created"):
                continue

            setattr(version_obj, field.name, getattr(self, field.name))

        version_obj.save()

        return self

    def update_with_version(self, **kwargs):
        """Update object and create new version object."""

        # Update current object
        for k, v in kwargs.items():
            setattr(self, k, v)

        return self.save_with_version()

    def delete_with_version(self):
        """Mark object as deleted and create new version object."""

        self.status = OBJECT_STATUS_DELETED
        return self.save_with_version()

    def get_detail_url(self, user):
        class_name = self.__class__.__name__.lower()

        if user.is_hpcadmin:
            section = "adminsec"

        else:
            section = "usersec"

        return reverse("{}:{}-detail".format(section, class_name), kwargs={class_name: self.uuid})


class RequestManagerMixin:
    def retract_with_version(self):
        """Mark object as retracted and create new version object."""

        self.status = REQUEST_STATUS_RETRACTED
        return self.save_with_version()

    def deny_with_version(self):
        """Mark object as denied and create new version object."""

        self.status = REQUEST_STATUS_DENIED
        return self.save_with_version()

    def approve_with_version(self):
        """Mark object as approved and create new version object."""

        self.status = REQUEST_STATUS_APPROVED
        return self.save_with_version()

    def revision_with_version(self):
        """Mark object as revision and create new version object."""

        self.status = REQUEST_STATUS_REVISION
        return self.save_with_version()

    def revised_with_version(self):
        """Mark object as revised and create new version object."""

        self.status = REQUEST_STATUS_REVISED
        return self.save_with_version()

    def get_revision_url(self):
        class_name = self.__class__.__name__.lower()
        return reverse("adminsec:{}-revision".format(class_name), kwargs={class_name: self.uuid})

    def get_approve_url(self):
        class_name = self.__class__.__name__.lower()
        return reverse("adminsec:{}-approve".format(class_name), kwargs={class_name: self.uuid})

    def get_deny_url(self):
        class_name = self.__class__.__name__.lower()
        return reverse("adminsec:{}-deny".format(class_name), kwargs={class_name: self.uuid})

    def get_update_url(self):
        class_name = self.__class__.__name__.lower()
        return reverse("usersec:{}-update".format(class_name), kwargs={class_name: self.uuid})

    def get_reactivate_url(self):
        class_name = self.__class__.__name__.lower()
        return reverse("usersec:{}-reactivate".format(class_name), kwargs={class_name: self.uuid})

    def get_retract_url(self):
        class_name = self.__class__.__name__.lower()
        return reverse("usersec:{}-retract".format(class_name), kwargs={class_name: self.uuid})


# ------------------------------------------------------------------------------
# Base model for Hpc objects
# ------------------------------------------------------------------------------


class HpcObjectAbstract(models.Model):
    """Common fields for HPC models"""

    class Meta:
        abstract = True

    #: Uuid
    uuid = models.UUIDField(default=uuid_object.uuid4, unique=True, help_text="Record UUID")

    #: Date created
    date_created = models.DateTimeField(auto_now_add=True, help_text="DateTime of creation")


# ------------------------------------------------------------------------------
# HpcUser related
# ------------------------------------------------------------------------------


class HpcUserAbstract(HpcObjectAbstract):
    """HpcUser abstract base class"""

    class Meta:
        abstract = True

    #: Associated Django user.
    user = models.ForeignKey(
        User,
        related_name="%(class)s_user",
        help_text="Associated Django user",
        null=True,
        on_delete=models.SET_NULL,
    )

    #: Primary group the user belongs to.
    primary_group = models.ForeignKey(
        "HpcGroup",
        related_name="%(class)s",
        help_text="Primary group the user belongs to",
        on_delete=models.CASCADE,
    )

    #: Users requested resources as JSON.
    resources_requested = models.JSONField()

    #: Users used resources as JSON.
    resources_used = models.JSONField(null=True, blank=True)

    #: Django user creating the object.
    creator = models.ForeignKey(
        User,
        related_name="%(class)s_creator",
        help_text="User creating the object",
        null=True,
        on_delete=models.SET_NULL,
    )

    #: Status of the object.
    status = models.CharField(
        max_length=16,
        choices=OBJECT_STATUS_CHOICES,
        default=OBJECT_STATUS_INITIAL,
        help_text="Status of the user object",
    )

    #: Any additional information about the user.
    description = models.CharField(
        max_length=512,
        null=True,
        help_text="Additional information about the user",
    )

    #: POSIX id of the user on the cluster.
    uid = models.IntegerField(null=True, help_text="Id of the user on the cluster")

    #: POSIX username on the cluster.
    username = models.CharField(max_length=32, help_text="Username of the user on the cluster")

    #: Expiration date of the user account
    expiration = models.DateTimeField(help_text="Expiration date of the user account")


class HpcUser(VersionManagerMixin, HpcUserAbstract):
    """HpcUser model"""

    #: Set custom manager
    objects = VersionManager()

    class Meta:
        unique_together = ("username",)

    #: Currently active version of the user object.
    current_version = models.IntegerField(help_text="Currently active version of the user object")

    def __repr__(self):
        return "{}(id={},user={},username={},uid={},primary_group={},status={},creator={},current_version={})".format(
            self.__class__.__name__,
            self.id,
            self.user.username if self.user else "None",
            self.username,
            self.uid,
            self.primary_group.name,
            self.status,
            self.creator.username,
            self.current_version,
        )

    def __str__(self):
        return "{} ({})".format(
            self.user.name if self.user else "User not connected", self.username
        )


class HpcUserVersion(HpcUserAbstract):
    """HpcUserVersion model"""

    class Meta:
        unique_together = ("username", "version")

    #: Version number of the user object.
    version = models.IntegerField(help_text="Version of this user object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcUser,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )

    def __repr__(self):
        return "{}(id={},user={},username={},uid={},primary_group={},status={},creator={},version={})".format(
            self.__class__.__name__,
            self.id,
            self.user.username if self.user else "None",
            self.username,
            self.uid,
            self.primary_group.name,
            self.status,
            self.creator.username,
            self.version,
        )


# ------------------------------------------------------------------------------
# HpcGroup related
# ------------------------------------------------------------------------------


class HpcGroupAbstract(HpcObjectAbstract):
    """HpcGroup abstract base class"""

    class Meta:
        abstract = True

    #: Owner of the group.
    owner = models.ForeignKey(
        HpcUser,
        related_name="%(class)s_owner",
        # Must be nullable because user and group reference each other
        # TODO: make sure there are no permanent owner-less groups
        null=True,
        help_text="User registered as owner of the group",
        on_delete=models.CASCADE,
    )

    #: Delegate of the group, optional.
    delegate = models.ForeignKey(
        HpcUser,
        related_name="%(class)s_delegate",
        null=True,
        blank=True,
        help_text="User registered as delegate of the group",
        on_delete=models.SET_NULL,
    )

    #: Groups requested resources as JSON.
    resources_requested = models.JSONField()

    #: Groups used resources as JSON.
    resources_used = models.JSONField(null=True, blank=True)

    #: Description of what the group is working on.
    description = models.CharField(max_length=512, help_text="Description of the groups work")

    #: Django User creating the object.
    creator = models.ForeignKey(
        User,
        related_name="%(class)s_creator",
        help_text="User creating the object",
        null=True,
        on_delete=models.SET_NULL,
    )

    #: Status of the object.
    status = models.CharField(
        max_length=16,
        choices=OBJECT_STATUS_CHOICES,
        default=OBJECT_STATUS_INITIAL,
        help_text="Status of the group object",
    )

    #: POSIX id of the group on the cluster.
    gid = models.IntegerField(null=True, help_text="Id of the group on the cluster")

    #: POSIX name of the group on the cluster.
    name = models.CharField(max_length=64, help_text="Name of the group on the cluster")

    #: Folder ot the group on the cluster.
    folder = models.CharField(max_length=64, help_text="Path to the group folder on the cluster")

    #: Expiration date of the group
    expiration = models.DateTimeField(help_text="Expiration date of the group")


class HpcGroup(VersionManagerMixin, HpcGroupAbstract):
    """HpcGroup model"""

    #: Set custom manager
    objects = VersionManager()

    class Meta:
        unique_together = ("name",)

    #: Currently active version of the group object.
    current_version = models.IntegerField(help_text="Currently active version of the group object")

    def __repr__(self):
        return "{}(id={},name={},owner={},delegate={},gid={},status={},creator={},current_version={})".format(
            self.__class__.__name__,
            self.id,
            self.name,
            self.owner.username,
            self.delegate.username if self.delegate else None,
            self.gid,
            self.status,
            self.creator.username,
            self.current_version,
        )

    def __str__(self):
        return "{} ({}, {})".format(
            self.name,
            self.owner.username,
            self.delegate.username if self.delegate else None,
        )


class HpcGroupVersion(HpcGroupAbstract):
    """HpcGroupVersion model"""

    class Meta:
        unique_together = ("name", "version")

    #: Version number of the group object.
    version = models.IntegerField(help_text="Version number of this group object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcGroup,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )

    def __repr__(self):
        return "{}(id={},name={},owner={},delegate={},gid={},status={},members={},creator={},version={})".format(
            self.__class__.__name__,
            self.id,
            self.name,
            self.owner.username,
            self.delegate.username if self.delegate else None,
            self.gid,
            self.status,
            self.hpcuser.count(),
            self.creator.username,
            self.version,
        )


# ------------------------------------------------------------------------------
# HpcProject related
# ------------------------------------------------------------------------------


class HpcProjectAbstract(HpcObjectAbstract):
    """HpcProject abstract base class"""

    class Meta:
        abstract = True

    #: Group that requested the project. Group PI is owner of project.
    group = models.ForeignKey(
        HpcGroup,
        related_name="%(class)s",
        help_text="Group that requested project. Group PI is owner of project",
        on_delete=models.CASCADE,
    )

    #: Delegate of the project, optional.
    delegate = models.ForeignKey(
        HpcUser,
        related_name="%(class)s_delegate",
        null=True,
        blank=True,
        help_text="User registered as delegate of the project",
        on_delete=models.SET_NULL,
    )

    #: Members of the project.
    members = models.ManyToManyField(
        HpcUser,
        related_name="%(class)s_members",
        help_text="Members of the project",
    )

    #: Projects requested resources as JSON.
    resources_requested = models.JSONField()

    #: Projects used resources as JSON.
    resources_used = models.JSONField(null=True, blank=True)

    #: Description of what the project is working on.
    description = models.CharField(max_length=512, help_text="Description of the groups work")

    #: Django User creating the object.
    creator = models.ForeignKey(
        User,
        related_name="%(class)s_creator",
        help_text="User creating the object",
        null=True,
        on_delete=models.SET_NULL,
    )

    #: Status of the object.
    status = models.CharField(
        max_length=16,
        choices=OBJECT_STATUS_CHOICES,
        default=OBJECT_STATUS_INITIAL,
        help_text="Status of the project object",
    )

    #: POSIX id of the project on the cluster.
    gid = models.IntegerField(null=True, help_text="Id of the project on the cluster")

    #: POSIX name of the project on the cluster.
    name = models.CharField(max_length=64, help_text="Name of the project on the cluster")

    #: Folder ot the project on the cluster.
    folder = models.CharField(max_length=64, help_text="Path to the project folder on the cluster")

    #: Expiration date of the project
    expiration = models.DateTimeField(help_text="Expiration date of the project")


class HpcProject(VersionManagerMixin, HpcProjectAbstract):
    """HpcProject model"""

    #: Set custom manager
    objects = VersionManager()

    class Meta:
        unique_together = ("name",)

    #: Currently active version of the project object.
    current_version = models.IntegerField(
        help_text="Currently active version of the project object"
    )

    def __repr__(self):
        return (
            "{}(id={},name={},group={},delegate={},gid={},status={},members={},creator={},"
            "current_version={})"
        ).format(
            self.__class__.__name__,
            self.id,
            self.name,
            self.group.name,
            self.delegate.username if self.delegate else None,
            self.gid,
            self.status,
            self.members.count(),
            self.creator.username,
            self.current_version,
        )

    def __str__(self):
        return "{} (owner: {}, delegate: {})".format(
            self.name,
            self.group.owner.username,
            self.delegate.username if self.delegate else None,
        )


class HpcProjectVersion(HpcProjectAbstract):
    """HpcProjectVersion model"""

    class Meta:
        unique_together = ("name", "version")

    #: Version number of the project object.
    version = models.IntegerField(help_text="Version number of this project object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcProject,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )

    def __repr__(self):
        return "{}(id={},name={},group={},delegate={},gid={},status={},members={},creator={},version={})".format(
            self.__class__.__name__,
            self.id,
            self.name,
            self.group.name,
            self.delegate.username if self.delegate else None,
            self.gid,
            self.status,
            self.members.count(),
            self.creator.username,
            self.version,
        )


# ------------------------------------------------------------------------------
# HpcRequest related
# ------------------------------------------------------------------------------


class HpcRequestAbstract(HpcObjectAbstract):
    """HpcRequest abstract base class"""

    class Meta:
        abstract = True

    #: User creating the object. Should never change.
    requester = models.ForeignKey(
        User,
        related_name="%(class)s_requester",
        help_text="User creating the request",
        null=True,
        on_delete=models.SET_NULL,
    )

    #: User editing the object.
    editor = models.ForeignKey(
        User,
        related_name="%(class)s_editor",
        help_text="User editing the request",
        null=True,
        on_delete=models.SET_NULL,
    )

    #: Status of the request.
    status = models.CharField(
        max_length=16,
        choices=REQUEST_STATUS_CHOICES,
        default=REQUEST_STATUS_INITIAL,
        help_text="Status of the request",
    )

    #: Comment for communication.
    comment = models.TextField(help_text="Comment request or summarize revision")

    def get_comment_history(self):
        history = self.version_history.exclude(comment__exact="").exclude(comment__isnull=True)
        comments = []

        for h in history:
            comments.append((h.editor.username, h.date_created, h.comment))

        return comments

    def is_decided(self):
        return self.status in (
            REQUEST_STATUS_DENIED,
            REQUEST_STATUS_APPROVED,
        )

    def is_denied(self):
        return self.status == REQUEST_STATUS_DENIED

    def is_retracted(self):
        return self.status == REQUEST_STATUS_RETRACTED

    def is_approved(self):
        return self.status == REQUEST_STATUS_APPROVED

    def is_active(self):
        return self.status in (
            REQUEST_STATUS_ACTIVE,
            REQUEST_STATUS_REVISED,
        )

    def is_revised(self):
        return self.status == REQUEST_STATUS_REVISED

    def is_revision(self):
        return self.status == REQUEST_STATUS_REVISION


# HpcGroupRequest related
# ------------------------------------------------------------------------------


class HpcGroupRequestAbstract(HpcRequestAbstract):
    """HpcGroupRequest abstract base class"""

    class Meta:
        abstract = True

    #: Group the request belongs to.
    group = models.ForeignKey(
        HpcGroup,
        related_name="%(class)s",
        help_text="Group the request belongs to",
        null=True,
        on_delete=models.CASCADE,
    )


# HpcGroupCreateRequest related
# ------------------------------------------------------------------------------


class HpcGroupCreateRequestAbstract(HpcGroupRequestAbstract):
    """HpcGroupCreateRequest abstract base class"""

    class Meta:
        abstract = True

    #: Groups requested resources as JSON.
    resources_requested = models.JSONField()

    #: Description of what the group is working on.
    description = models.CharField(max_length=512, help_text="Description of the groups work")

    #: Expiration date of the group.
    expiration = models.DateTimeField(help_text="Expiration date of the group")


class HpcGroupCreateRequest(
    RequestManagerMixin, VersionManagerMixin, HpcGroupCreateRequestAbstract
):
    """HpcGroupCreateRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the group create request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the group create request object"
    )


class HpcGroupCreateRequestVersion(HpcGroupCreateRequestAbstract):
    """HpcGroupCreateRequestVersion model"""

    class Meta:
        unique_together = ("belongs_to", "version")

    #: Version number of the group create request object.
    version = models.IntegerField(help_text="Version number of this group create request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcGroupCreateRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# HpcGroupChangeRequest related
# ------------------------------------------------------------------------------


class HpcGroupChangeRequestAbstract(HpcGroupRequestAbstract):
    """HpcGroupChangeRequest abstract base class"""

    class Meta:
        abstract = True

    #: Groups requested resources as JSON.
    resources_requested = models.JSONField()

    #: Delegate of the group, optional.
    delegate = models.ForeignKey(
        HpcUser,
        related_name="%(class)s_delegate",
        null=True,
        blank=True,
        help_text="User registered as delegate of the group",
        on_delete=models.SET_NULL,
    )

    #: Expiration date of the group
    expiration = models.DateTimeField(help_text="Expiration date of the group")


class HpcGroupChangeRequest(
    RequestManagerMixin, VersionManagerMixin, HpcGroupChangeRequestAbstract
):
    """HpcGroupChangeRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the group change request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the group change request object"
    )


class HpcGroupChangeRequestVersion(HpcGroupChangeRequestAbstract):
    """HpcGroupChangeRequestVersion model"""

    class Meta:
        unique_together = ("belongs_to", "version")

    #: Version number of the group change request object.
    version = models.IntegerField(help_text="Version number of this group change request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcGroupChangeRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# HpcGroupDeleteRequest related
# ------------------------------------------------------------------------------


class HpcGroupDeleteRequest(RequestManagerMixin, VersionManagerMixin, HpcGroupRequestAbstract):
    """HpcGroupDeleteRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the group delete request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the group delete request object"
    )


class HpcGroupDeleteRequestVersion(HpcGroupRequestAbstract):
    """HpcGroupDeleteRequestVersion model"""

    class Meta:
        unique_together = ("belongs_to", "version")

    #: Version number of the group delete request object.
    version = models.IntegerField(help_text="Version number of this group delete request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcGroupDeleteRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# ------------------------------------------------------------------------------
# HpcUserRequest related
# ------------------------------------------------------------------------------


class HpcUserRequestAbstract(HpcRequestAbstract):
    """HpcUserRequest abstract base class"""

    class Meta:
        abstract = True

    #: User the request belongs to.
    user = models.ForeignKey(
        HpcUser,
        related_name="%(class)s",
        help_text="User the request belongs to",
        null=True,
        on_delete=models.CASCADE,
    )


# HpcUserCreateRequest related
# ------------------------------------------------------------------------------


class HpcUserCreateRequestAbstract(HpcUserRequestAbstract):
    """HpcUserCreateRequest abstract base class"""

    class Meta:
        abstract = True

    #: Users requested resources as JSON.
    resources_requested = models.JSONField()

    #: Email of the user to send an invitation to.
    email = models.EmailField(
        null=False, blank=False, help_text="Email of user to send an invitation to"
    )

    #: Group the request belongs to.
    group = models.ForeignKey(
        HpcGroup,
        related_name="%(class)s",
        help_text="Group the request belongs to",
        null=True,
        on_delete=models.CASCADE,
    )

    #: Expiration date of the user
    expiration = models.DateTimeField(help_text="Expiration date of the user")


class HpcUserCreateRequest(RequestManagerMixin, VersionManagerMixin, HpcUserCreateRequestAbstract):
    """HpcUserCreateRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the user create request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the user create request object"
    )


class HpcUserCreateRequestVersion(HpcUserCreateRequestAbstract):
    """HpcUserCreateRequestVersion model"""

    #: Version number of the user create request object.
    version = models.IntegerField(help_text="Version number of this user create request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcUserCreateRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# HpcUserChangeRequest related
# ------------------------------------------------------------------------------


class HpcUserChangeRequestAbstract(HpcUserRequestAbstract):
    """HpcUserChangeRequest abstract base class"""

    class Meta:
        abstract = True

    #: Users requested resources as JSON.
    resources_requested = models.JSONField()

    #: Expiration date of the user
    expiration = models.DateTimeField(help_text="Expiration date of the user")


class HpcUserChangeRequest(RequestManagerMixin, VersionManagerMixin, HpcUserChangeRequestAbstract):
    """HpcUserChangeRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the user change request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the user change request object"
    )


class HpcUserChangeRequestVersion(HpcUserChangeRequestAbstract):
    """HpcUserChangeRequestVersion model"""

    class Meta:
        unique_together = ("belongs_to", "version")

    #: Version number of the user change request object.
    version = models.IntegerField(help_text="Version number of this user change request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcUserChangeRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# HpcUserDeleteRequest related
# ------------------------------------------------------------------------------


class HpcUserDeleteRequest(RequestManagerMixin, VersionManagerMixin, HpcUserRequestAbstract):
    """HpcUserDeleteRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the user delete request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the user delete request object"
    )


class HpcUserDeleteRequestVersion(HpcUserRequestAbstract):
    """HpcUserDeleteRequestVersion model"""

    class Meta:
        unique_together = ("belongs_to", "version")

    #: Version number of the user delete request object.
    version = models.IntegerField(help_text="Version number of this user delete request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcUserDeleteRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# ------------------------------------------------------------------------------
# HpcProjectRequest related
# ------------------------------------------------------------------------------


class HpcProjectRequestAbstract(HpcRequestAbstract):
    """HpcProjectRequest abstract base class"""

    class Meta:
        abstract = True

    #: Project the request belongs to.
    project = models.ForeignKey(
        HpcProject,
        related_name="%(class)s",
        help_text="Project the request belongs to",
        null=True,
        on_delete=models.CASCADE,
    )


# HpcProjectCreateRequest related
# ------------------------------------------------------------------------------


class HpcProjectCreateRequestAbstract(HpcProjectRequestAbstract):
    """HpcProjectCreateRequest abstract base class"""

    class Meta:
        abstract = True

    #: Projects requested resources as JSON.
    resources_requested = models.JSONField()

    #: Group the request belongs to.
    group = models.ForeignKey(
        HpcGroup,
        related_name="%(class)s",
        help_text="Group the request belongs to",
        on_delete=models.CASCADE,
    )

    #: Delegate of the project, optional.
    delegate = models.ForeignKey(
        HpcUser,
        related_name="%(class)s_delegate",
        null=True,
        blank=True,
        help_text="User registered as delegate of the project",
        on_delete=models.SET_NULL,
    )

    #: Members of the project.
    members = models.ManyToManyField(
        HpcUser,
        related_name="%(class)s_members",
        help_text="Members of the project",
    )

    #: Name of the project
    name = models.CharField(max_length=512, help_text="Description of the groups work")

    #: Description of the project.
    description = models.CharField(
        max_length=512,
        help_text="Additional information about the user",
    )

    #: Expiration date of the project
    expiration = models.DateTimeField(help_text="Expiration date of the project")


class HpcProjectCreateRequest(
    RequestManagerMixin, VersionManagerMixin, HpcProjectCreateRequestAbstract
):
    """HpcProjectCreateRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the project create request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the project create request object"
    )


class HpcProjectCreateRequestVersion(HpcProjectCreateRequestAbstract):
    """HpcProjectCreateRequestVersion model"""

    #: Version number of the project create request object.
    version = models.IntegerField(help_text="Version number of this project create request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcProjectCreateRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# HpcProjectChangeRequest related
# ------------------------------------------------------------------------------


class HpcProjectChangeRequestAbstract(HpcProjectRequestAbstract):
    """HpcProjectChangeRequest abstract base class"""

    class Meta:
        abstract = True

    #: Projects requested resources as JSON.
    resources_requested = models.JSONField()

    #: Delegate of the project, optional.
    delegate = models.ForeignKey(
        HpcUser,
        related_name="%(class)s_delegate",
        null=True,
        blank=True,
        help_text="User registered as delegate of the project",
        on_delete=models.SET_NULL,
    )

    #: Members of the project.
    members = models.ManyToManyField(
        HpcUser,
        related_name="%(class)s_members",
        help_text="Members of the project",
    )

    #: Description of the project.
    description = models.CharField(
        max_length=512,
        null=True,
        help_text="Additional information about the user",
    )

    #: Expiration date of the project
    expiration = models.DateTimeField(help_text="Expiration date of the project")


class HpcProjectChangeRequest(
    RequestManagerMixin, VersionManagerMixin, HpcProjectChangeRequestAbstract
):
    """HpcProjectChangeRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the project change request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the project change request object"
    )


class HpcProjectChangeRequestVersion(HpcProjectChangeRequestAbstract):
    """HpcProjectChangeRequestVersion model"""

    class Meta:
        unique_together = ("belongs_to", "version")

    #: Version number of the project change request object.
    version = models.IntegerField(help_text="Version number of this project change request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcProjectChangeRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# HpcProjectDeleteRequest related
# ------------------------------------------------------------------------------


class HpcProjectDeleteRequest(RequestManagerMixin, VersionManagerMixin, HpcProjectRequestAbstract):
    """HpcProjectDeleteRequest model"""

    #: Set custom manager
    objects = VersionRequestManager()

    #: Currently active version of the project delete request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the project delete request object"
    )


class HpcProjectDeleteRequestVersion(HpcProjectRequestAbstract):
    """HpcProjectDeleteRequestVersion model"""

    class Meta:
        unique_together = ("belongs_to", "version")

    #: Version number of the project delete request object.
    version = models.IntegerField(help_text="Version number of this project delete request object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcProjectDeleteRequest,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )
