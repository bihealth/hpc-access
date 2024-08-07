import re
import uuid as uuid_object
from enum import Enum, unique

from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from factory.django import get_model

from adminsec.constants import TIER_USER_HOME
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

#: Invitation created and waiting for decision.
INVITATION_STATUS_PENDING = "PENDING"

#: Invitation rejected by user.
INVITATION_STATUS_REJECTED = "REJECTED"

#: Invitation accepted by user.
INVITATION_STATUS_ACCEPTED = "ACCEPTED"

#: Invitation accepted by user.
INVITATION_STATUS_EXPIRED = "EXPIRED"

#: Choices of invitation status.
INVITATION_STATUS_CHOICES = (
    (INVITATION_STATUS_PENDING, INVITATION_STATUS_PENDING),
    (INVITATION_STATUS_ACCEPTED, INVITATION_STATUS_ACCEPTED),
    (INVITATION_STATUS_REJECTED, INVITATION_STATUS_REJECTED),
    (INVITATION_STATUS_EXPIRED, INVITATION_STATUS_EXPIRED),
)

#: Login shell bash.
LOGIN_SHELL_BASH = "/usr/bin/bash"

#: Login shell fish.
LOGIN_SHELL_FISH = "/usr/bin/fish"

#: Login shell zsh.
LOGIN_SHELL_ZSH = "/usr/bin/zsh"

#: Login shell sh.
LOGIN_SHELL_SH = "/usr/bin/sh"

#: Login shell choices.
LOGIN_SHELL_CHOICES = [
    (LOGIN_SHELL_BASH, LOGIN_SHELL_BASH),
    (LOGIN_SHELL_FISH, LOGIN_SHELL_FISH),
    (LOGIN_SHELL_ZSH, LOGIN_SHELL_ZSH),
    (LOGIN_SHELL_SH, LOGIN_SHELL_SH),
]


RE_EMAIL = r"^\S+@\S+\.\S+$"


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


@unique
class HpcQuotaStatus(Enum):
    GREEN = 1
    YELLOW = 2
    RED = 3

    def __ge__(self, other):
        return self.value >= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __le__(self, other):
        return self.value <= other.value

    def __lt__(self, other):
        return self.value < other.value


class CheckQuotaMixin:
    def generate_quota_report(self):
        """Generate a quota report for the object."""
        if not hasattr(self, "resources_requested") or not hasattr(self, "resources_used"):
            # Sanity check - probably wrong use of mixin
            raise AttributeError("Object does not have resources_requested or resources_used")

        requested = set((self.resources_requested or {}).keys())
        used = set((self.resources_used or {}).keys())
        available = requested & used
        if not available:
            return {
                "used": {},
                "requested": {},
                "percentage": {},
                "status": {},
                "folders": {},
                "warnings": ["No resources available."],
            }
        folders = (
            {TIER_USER_HOME: self.home_directory}
            if isinstance(self, get_model(APP_NAME, "HpcUser"))
            else getattr(self, "folders", {})
        )
        result = {
            "used": {a: self.resources_used[a] for a in available},
            "requested": {a: self.resources_requested[a] for a in available},
            "percentage": {},
            "status": {},
            "folders": {a: folders[a] for a in available},
            "warnings": [],
        }

        for key in used - requested:
            result["warnings"].append(
                f"Resource {key} is used, but not found in requested resources"
            )

        for key in requested - used:
            result["warnings"].append(
                f"Resource {key} is requested, but not found in used resources"
            )

        for key in available:
            used_val = self.resources_used.get(key)
            requested_val = self.resources_requested.get(key)

            if requested_val == 0 or used_val == 0:
                # if requested_val is 0, CEPHFS provides unlimited quota => status always green
                # if used_val is 0, the user has not used any resources => cut short
                result["percentage"][key] = 0
                result["status"][key] = HpcQuotaStatus.GREEN
                continue

            result["percentage"][key] = round(100 * used_val / requested_val)

            if used_val >= requested_val:
                result["status"][key] = HpcQuotaStatus.RED

            elif used_val >= max(
                requested_val * settings.QUOTA_WARNING_THRESHOLD / 100,
                requested_val - settings.QUOTA_WARNING_ABSOLUTE,
            ):
                result["status"][key] = HpcQuotaStatus.YELLOW

            else:
                result["status"][key] = HpcQuotaStatus.GREEN

        return result


def parse_email(email):
    if not email:
        raise ValueError("Email is empty")

    if re.match(RE_EMAIL, email) is None:
        raise ValueError("Email is not valid")

    return email


def user_active(hpcuser):
    return (
        hpcuser.user.is_active
        and hpcuser.login_shell != "/usr/sbin/nologin"
        and hpcuser.status != "EXPIRED"
    )


class ContactMixin:
    def get_manager_emails(self, slim=True):
        if isinstance(self, get_model(APP_NAME, "HpcUser")):
            raise NotImplementedError("Method only implemented for Hpc{Group,Project} objects")
        elif isinstance(self, get_model(APP_NAME, "HpcGroup")):
            owner_email = self.owner.user.email
        elif isinstance(self, get_model(APP_NAME, "HpcProject")):
            owner_email = self.group.owner.user.email

        try:
            owner_email = parse_email(owner_email)
        except ValueError:
            owner_email = None

        try:
            delegate_email = parse_email(self.delegate.user.email if self.delegate else None)
        except ValueError:
            delegate_email = None

        emails = {}

        if delegate_email:
            emails["delegate"] = delegate_email

        if owner_email and (not slim or not delegate_email):
            emails["owner"] = owner_email

        return emails

    def get_manager_names(self, slim=True):
        if isinstance(self, get_model(APP_NAME, "HpcUser")):
            raise NotImplementedError("Method only implemented for Hpc{Group,Project} objects")
        elif isinstance(self, get_model(APP_NAME, "HpcGroup")):
            owner_name = self.owner.user.get_full_name()
        elif isinstance(self, get_model(APP_NAME, "HpcProject")):
            owner_name = self.group.owner.user.get_full_name()

        delegate_name = self.delegate.user.get_full_name() if self.delegate else None
        names = {}

        if delegate_name:
            names["delegate"] = delegate_name

        if not slim or not delegate_name:
            names["owner"] = owner_name

        return names

    def get_manager_active(self, slim=True):
        if isinstance(self, get_model(APP_NAME, "HpcUser")):
            raise NotImplementedError("Method only implemented for Hpc{Group,Project} objects")
        elif isinstance(self, get_model(APP_NAME, "HpcGroup")):
            owner_active = user_active(self.owner)
        elif isinstance(self, get_model(APP_NAME, "HpcProject")):
            owner_active = user_active(self.group.owner)

        delegate_active = user_active(self.delegate) if self.delegate else None
        active = []

        if delegate_active:
            active.append("delegate")

        if owner_active and (not slim or not delegate_active):
            active.append("owner")

        return active

    def get_manager_contact(self, slim=True):
        if isinstance(self, get_model(APP_NAME, "HpcUser")):
            raise NotImplementedError("Method only implemented for Hpc{Group,Project} objects")

        emails = self.get_manager_emails(slim)
        names = self.get_manager_names(slim)
        active = self.get_manager_active(slim)

        # Don't return contact info where there is no email available
        contacts = {n: {} for n in set(emails.keys()) & set(names.keys()) & set(active)}

        for name in contacts.keys():
            contacts[name]["email"] = emails[name]
            contacts[name]["name"] = names[name]

        return contacts

    def get_user_active(self):
        if not isinstance(self, get_model(APP_NAME, "HpcUser")):
            raise NotImplementedError("Method only implemented for HpcUser objects")

        return user_active(self)

    def get_user_email(self):
        if not isinstance(self, get_model(APP_NAME, "HpcUser")):
            raise NotImplementedError("Method only implemented for HpcUser objects")

        if not self.get_user_active():
            return None

        try:
            return parse_email(self.user.email)

        except ValueError:
            return None


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
        null=True,
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
        blank=True,
        help_text="Additional information about the user",
    )

    #: POSIX username on the cluster.
    username = models.CharField(max_length=32, help_text="Username of the user on the cluster")

    #: Expiration date of the user account
    expiration = models.DateTimeField(help_text="Expiration date of the user account")

    #: Home directory of the user on the cluster.
    home_directory = models.CharField(
        max_length=64,
        help_text="Path to the user home directory on the cluster",
    )

    #: Login shell of the user on the cluster.
    login_shell = models.CharField(
        max_length=32,
        help_text="Login shell of the user on the cluster",
        choices=LOGIN_SHELL_CHOICES,
        default=LOGIN_SHELL_BASH,
    )


class HpcUser(ContactMixin, VersionManagerMixin, CheckQuotaMixin, HpcUserAbstract):
    """HpcUser model"""

    #: Set custom manager
    objects = VersionManager()

    class Meta:
        unique_together = ("username",)

    #: Currently active version of the user object.
    current_version = models.IntegerField(help_text="Currently active version of the user object")

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f"user={self.user.username if self.user else None},"
            f"username={self.username},"
            f"uid={self.user.uid if self.user else None},"
            f"primary_group={self.primary_group.name},"
            f"status={self.status},"
            f"creator={self.creator.username if self.creator else None},"
            f"current_version={self.current_version})"
        )

    def __str__(self):
        return "{} ({})".format(
            ", ".join([self.user.last_name, self.user.first_name]), self.username
        )

    def get_pending_invitations(self):
        return self.hpcprojectinvitations.filter(status=INVITATION_STATUS_PENDING)

    @property
    def is_pi(self):
        return self.primary_group.owner == self


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
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f"user={self.user.username if self.user else None},"
            f"username={self.username},"
            f"uid={self.uid},"
            f"primary_group={self.primary_group.name},"
            f"status={self.status},"
            f"creator={self.creator.username if self.creator else None},"
            f"version={self.version})"
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
        help_text="The optional delegate can act on behalf of the project owner",
        on_delete=models.SET_NULL,
    )

    #: Groups requested resources as JSON.
    resources_requested = models.JSONField()

    #: Groups used resources as JSON.
    resources_used = models.JSONField(null=True, blank=True)

    #: Description of what the group is working on.
    description = models.CharField(
        max_length=512,
        help_text=(
            "Concise description of what kind of computations the group performs on the cluster"
        ),
        null=True,
        blank=True,
    )

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

    #: Folders of the group on the cluster.
    folders = models.JSONField(help_text="Paths to the folders of the group on the cluster")

    #: Expiration date of the group
    expiration = models.DateTimeField(help_text="Expiration date of the group")


class HpcGroup(ContactMixin, VersionManagerMixin, CheckQuotaMixin, HpcGroupAbstract):
    """HpcGroup model"""

    #: Set custom manager
    objects = VersionManager()

    class Meta:
        unique_together = ("name",)

    #: Currently active version of the group object.
    current_version = models.IntegerField(help_text="Currently active version of the group object")

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f"name={self.name},"
            f"owner={self.owner.username},"
            f"delegate={self.delegate.username if self.delegate else None},"
            f"gid={self.gid},"
            f"status={self.status},"
            f"creator={self.creator.username if self.creator else None},"
            f"current_version={self.current_version})"
        )

    def __str__(self):
        self_owner_username = None
        if self.owner:
            self_owner_username = self.owner.username
        self_delegate_username = None
        if self.delegate:
            self_delegate_username = self.delegate.username
        return "{} ({}, {})".format(
            self.name,
            self_owner_username,
            self_delegate_username,
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
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f"name={self.name},"
            f"owner={self.owner.username},"
            f"delegate={self.delegate.username if self.delegate else None},"
            f"gid={self.gid},"
            f"status={self.status},"
            f"members={self.hpcuser.count()},"
            f"creator={self.creator.username if self.creator else None},"
            f"version={self.version})"
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
        related_name="%(class)ss",
        help_text="Group that requested project. Group PI is owner of project",
        on_delete=models.CASCADE,
    )

    #: Delegate of the project, optional.
    delegate = models.ForeignKey(
        HpcUser,
        related_name="%(class)s_delegate",
        null=True,
        blank=True,
        help_text="The optional delegate can act on behalf of the project owner",
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
    description = models.CharField(
        max_length=512,
        help_text=(
            "Concise description of what kind of computations are required for the project on the "
            "cluster"
        ),
        null=True,
        blank=True,
    )

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

    #: Folders of the project on the cluster.
    folders = models.JSONField(help_text="Paths to the folders of the project on the cluster")

    #: Expiration date of the project
    expiration = models.DateTimeField(help_text="Expiration date of the project")


class HpcProject(ContactMixin, VersionManagerMixin, CheckQuotaMixin, HpcProjectAbstract):
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
            self.creator.username if self.creator else None,
            self.current_version,
        )

    def __str__(self):
        self_group_owner_username = None
        if self.group and self.group.owner:
            self_group_owner_username = self.group.owner.username
        self_delegate_username = None
        if self.delegate:
            self_delegate_username = self.delegate.username
        return "{} (owner: {}, delegate: {})".format(
            self.name,
            self_group_owner_username,
            self_delegate_username,
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
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f"name={self.name},"
            f"group={self.group.name},"
            f"delegate={self.delegate.username if self.delegate else None},"
            f"gid={self.gid},"
            f"status={self.status},"
            f"members={self.members.count()},"
            f"creator={self.creator.username if self.creator else None},"
            f"version={self.version})"
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
    comment = models.TextField(
        blank=True,
        null=True,
        help_text="This field is for communication between you and the HPC team.",
    )

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

    def display_status(self):
        mapping = {
            REQUEST_STATUS_INITIAL: "initial",
            REQUEST_STATUS_ACTIVE: "pending",
            REQUEST_STATUS_REVISION: "revision required",
            REQUEST_STATUS_REVISED: "pending (revised)",
            REQUEST_STATUS_APPROVED: "approved",
            REQUEST_STATUS_DENIED: "denied",
            REQUEST_STATUS_RETRACTED: "retracted",
        }

        return mapping.get(self.status, "unknown status")


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

    #: POSIX name of the group on the cluster.
    name = models.CharField(
        max_length=64, help_text="POSIX name of the group on the cluster", null=True, blank=True
    )

    #: Folders of the group on the cluster.
    folders = models.JSONField(
        help_text="Paths to the folders of the project on the cluster", null=True, blank=True
    )

    #: Description of what the group is working on.
    description = models.CharField(
        max_length=512,
        help_text=(
            "Concise description of what kind of computations the group performs on the cluster"
        ),
        null=True,
        blank=True,
    )

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

    def get_request_type(self):
        return "group create"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcgroupcreaterequest-detail", kwargs={"hpcgroupcreaterequest": self.uuid}
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
        help_text="The optional delegate can act on behalf of the group owner",
        on_delete=models.SET_NULL,
    )

    #: Description, optional.
    description = models.CharField(
        max_length=512,
        help_text=(
            "Concise description of what kind of computations are required for the project on the "
            "cluster"
        ),
        null=True,
        blank=True,
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

    def get_request_type(self):
        return "group change"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcgroupchangerequest-detail", kwargs={"hpcgroupchangerequest": self.uuid}
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

    def get_request_type(self):
        return "group delete"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcgroupdeleterequest-detail", kwargs={"hpcgroupdeleterequest": self.uuid}
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

    def get_request_type(self):
        return "user create"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcusercreaterequest-detail", kwargs={"hpcusercreaterequest": self.uuid}
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

    def get_request_type(self):
        return "user change"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcuserchangerequest-detail", kwargs={"hpcuserchangerequest": self.uuid}
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

    def get_request_type(self):
        return "user delete"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcuserdeleterequest-detail", kwargs={"hpcuserdeleterequest": self.uuid}
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

    #: Members of the project.
    members = models.ManyToManyField(
        HpcUser,
        related_name="%(class)s_members",
        help_text="Members of the project",
    )

    #: Requested project name
    name_requested = models.CharField(
        max_length=64,
        help_text="Please use only alphanumeric characters, dashes or underscores and no spaces",
    )

    #: POSIX id of the project on the cluster.
    name = models.CharField(
        max_length=64, help_text="POSIX name of the project on the cluster", null=True, blank=True
    )

    #: Folders ot the project on the cluster.
    folders = models.JSONField(
        help_text="Paths to the folders of the project on the cluster", null=True, blank=True
    )

    #: Description of the project.
    description = models.CharField(
        max_length=512,
        help_text=(
            "Concise description of what kind of computations are required for the project on the "
            "cluster",
        ),
        null=True,
        blank=True,
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

    def get_request_type(self):
        return "project create"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcprojectcreaterequest-detail",
            kwargs={"hpcprojectcreaterequest": self.uuid},
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
        help_text="The optional delegate can act on behalf of the project owner",
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
        blank=True,
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

    def get_request_type(self):
        return "project change"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcprojectchangerequest-detail",
            kwargs={"hpcprojectchangerequest": self.uuid},
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

    def get_request_type(self):
        return "project delete"

    def get_detail_path(self, admin=False):
        section = "adminsec" if admin else "usersec"
        return reverse(
            f"{section}:hpcprojectdeleterequest-detail",
            kwargs={"hpcprojectdeleterequest": self.uuid},
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


class HpcInvitationAbstract(HpcObjectAbstract):
    """HpcInvitation abstract base class."""

    class Meta:
        abstract = True

    #: Status of the object.
    status = models.CharField(
        max_length=16,
        choices=INVITATION_STATUS_CHOICES,
        default=INVITATION_STATUS_PENDING,
        help_text="Status of the project invitation",
    )


class HpcProjectInvitationAbstract(HpcInvitationAbstract):
    """HpcProjectInvitation abstract base class."""

    class Meta:
        abstract = True

    #: Link to HPC project
    project = models.ForeignKey(
        HpcProject, help_text="Project the user has been invited to", on_delete=models.CASCADE
    )

    #: Link to HPC project create request
    hpcprojectcreaterequest = models.ForeignKey(
        HpcProjectCreateRequest,
        help_text="Project create request that initiated the invitation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    #: Link to HPC project change request
    hpcprojectchangerequest = models.ForeignKey(
        HpcProjectChangeRequest,
        help_text="Project change request that initiated the invitation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    #: Link to HPC user
    user = models.ForeignKey(
        HpcUser, help_text="Invited user", on_delete=models.CASCADE, related_name="%(class)ss"
    )


class HpcProjectInvitation(VersionManagerMixin, HpcProjectInvitationAbstract):
    """HpcProjectInvitation model."""

    #: Set custom manager
    objects = VersionManager()

    #: Currently active version of the project delete request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the project delete request object"
    )

    def get_invitation_type(self):
        return "project"


class HpcProjectInvitationVersion(HpcProjectInvitationAbstract):
    """HpcProjectInvitationVersion model."""

    #: Version number of the project invitation object.
    version = models.IntegerField(help_text="Version number of this project invitation object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcProjectInvitation,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


class HpcGroupInvitationAbstract(HpcInvitationAbstract):
    """HpcGroupInvitation abstract base class."""

    class Meta:
        abstract = True

    #: Link to HPC user create request
    hpcusercreaterequest = models.ForeignKey(
        HpcUserCreateRequest,
        help_text="User create request that initiated the invitation",
        on_delete=models.CASCADE,
    )

    #: Username
    username = models.CharField(max_length=255, help_text="Username the invitation is valid for")


class HpcGroupInvitation(VersionManagerMixin, HpcGroupInvitationAbstract):
    """HpcGroupInvitation model."""

    #: Set custom manager
    objects = VersionManager()

    #: Currently active version of the group invitation object.
    current_version = models.IntegerField(
        help_text="Currently active version of the group invitation object"
    )

    def get_invitation_type(self):
        return "group"


class HpcGroupInvitationVersion(HpcGroupInvitationAbstract):
    """HpcGroupInvitationVersion model."""

    #: Version number of the group invitation object.
    version = models.IntegerField(help_text="Version number of this group invitation object")

    #: Link to actual (non-version) object.
    belongs_to = models.ForeignKey(
        HpcGroupInvitation,
        null=True,
        related_name="version_history",
        help_text="Object this version belongs to",
        on_delete=models.CASCADE,
    )


# ------------------------------------------------------------------------------
# Other models
# ------------------------------------------------------------------------------


#: Object is initialized.
TERMS_AUDIENCE_USER = "user"

#: Object is set active.
TERMS_AUDIENCE_PI = "pi"

#: Object marked as deleted.
TERMS_AUDIENCE_ALL = "all"

#: Group, project and user statuses.
TERMS_AUDIENCE_CHOICES = [
    (TERMS_AUDIENCE_USER, TERMS_AUDIENCE_USER),
    (TERMS_AUDIENCE_PI, TERMS_AUDIENCE_PI),
    (TERMS_AUDIENCE_ALL, TERMS_AUDIENCE_ALL),
]


class TermsAndConditions(HpcObjectAbstract):
    """Model for terms and conditions texts. Not an HpcObject, but requires same basics."""

    #: Date of modification.
    date_modified = models.DateTimeField(auto_now=True)

    #: Title.
    title = models.CharField(
        max_length=512, null=False, blank=False, help_text="Title of this terms and conditions leg."
    )

    #: Legal text.
    text = models.TextField(
        null=False, blank=False, help_text="Text of this terms and conditions leg."
    )

    #: Display text to ...
    audience = models.CharField(
        max_length=16,
        choices=TERMS_AUDIENCE_CHOICES,
        default=TERMS_AUDIENCE_ALL,
        help_text="Define the target audience of the text.",
    )

    #: Date of publication.
    date_published = models.DateTimeField(null=True, blank=True, help_text="Date of publication.")

    def __str__(self):
        return self.title
