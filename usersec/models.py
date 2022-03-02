from django.contrib.auth import user_logged_in
from django.db import models
import uuid as uuid_object

from hpcaccess.users.models import User


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

#: Request has been created and was not yet reviewed.
REQUEST_STATUS_INITIAL = "INITIAL"

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
    (REQUEST_STATUS_REVISION, REQUEST_STATUS_REVISION),
    (REQUEST_STATUS_REVISED, REQUEST_STATUS_REVISED),
    (REQUEST_STATUS_APPROVED, REQUEST_STATUS_APPROVED),
    (REQUEST_STATUS_DENIED, REQUEST_STATUS_DENIED),
    (REQUEST_STATUS_RETRACTED, REQUEST_STATUS_RETRACTED),
]


class HpcManager(models.Manager):
    """Manager class for HPC models"""

    def create_with_version(self):
        """Create HpcUser/HpcGroup and HpcUserVersion/HpcGroupVersion object."""

    def update_with_version(self):
        """Update HpcUser/HpcGroup and create HpcUserVersion/HpcGroupVersion object."""

    def delete_with_version(self):
        """Update HpcUser/HpcGroup and create HpcUserVersion/HpcGroupVersion object with status deleted."""


class HpcObjectAbstract(models.Model):
    """Common fields for HPC models"""

    class Meta:
        abstract = True

    #: Custom objects manager.
    objects = HpcManager()

    #: Uuid
    uuid = models.UUIDField(default=uuid_object.uuid4, unique=True, help_text="Record UUID")

    #: Date created
    date_created = models.DateTimeField(auto_now_add=True, help_text="DateTime of creation")


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
    resources_used = models.JSONField()

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
        max_length=16, choices=OBJECT_STATUS_CHOICES, help_text="Status of the user object"
    )

    #: Any additional information about the user.
    description = models.CharField(
        max_length=512, null=True, help_text="Additional information about the user"
    )

    #: POSIX id of the user on the cluster.
    uid = models.IntegerField(null=True, help_text="Id of the user on the cluster")

    #: POSIX username on the cluster.
    username = models.CharField(max_length=32, help_text="Username of the user on the cluster")

    #: First names of the user.
    first_names = models.CharField(max_length=32, help_text="First name(s) of the user")

    #: Family name of the user.
    surname = models.CharField(max_length=32, help_text="Surname of the user")

    #: Institutional email address of the user.
    email = models.CharField(max_length=512, help_text="Email address of the user")

    #: Institutional phone number of the user.
    phone = models.CharField(max_length=32, null=True, help_text="Telephone number of the user")

    #: Expiration date of the user account
    expiration = models.DateTimeField(help_text="Expiration date of the user account")


class HpcUser(HpcUserAbstract):
    """HpcUser model"""

    #: Currently active version of the user object.
    current_version = models.IntegerField(help_text="Currently active version of the user object")


class HpcUserVersion(HpcUserAbstract):
    """HpcUserVersion model"""

    #: Version number of the user object.
    version = models.IntegerField(help_text="Version of this user object")


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
    resources_used = models.JSONField()

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
        max_length=16, choices=OBJECT_STATUS_CHOICES, help_text="Status of the group object"
    )

    #: POSIX id of the group on the cluster.
    gid = models.IntegerField(null=True, help_text="Id of the group on the cluster")

    #: POSIX name of the group on the cluster.
    name = models.CharField(max_length=64)

    #: Folder ot the group on the cluster.
    folder = models.CharField(max_length=64)

    #: Expiration date of the group
    expiration = models.DateTimeField(help_text="Expiration date of the group")


class HpcGroup(HpcGroupAbstract):
    """HpcGroup model"""

    #: Currently active version of the group object.
    current_version = models.IntegerField(help_text="Currently active version of the group object")


class HpcGroupVersion(HpcGroupAbstract):
    """HpcGroupVersion model"""

    #: Version number of the group object.
    version = models.IntegerField(help_text="Version number of this group object")


class HpcGroupRequestAbstract(HpcObjectAbstract):
    """HpcGroupRequest abstract base class"""

    class Meta:
        abstract = True

    #: User creating the object.
    requester = models.ForeignKey(
        HpcUser,
        related_name="%(class)s_requester",
        help_text="User creating the request",
        null=True,
        on_delete=models.SET_NULL,
    )

    #: Group the user belongs to.
    group = models.ForeignKey(
        HpcGroup,
        related_name="%(class)s",
        help_text="Group the request belongs to",
        on_delete=models.CASCADE,
    )

    #: Status of the request.
    status = models.CharField(
        max_length=16, choices=REQUEST_STATUS_CHOICES, help_text="Status of the request"
    )

    #: Comment for communication.
    comment = models.CharField(max_length=1024, help_text="Comment on request or revision")


class HpcGroupChangeRequestAbstract(HpcGroupRequestAbstract):
    """HpcGroupChangeRequest abstract base class"""

    class Meta:
        abstract = True

    #: Groups requested resources as JSON.
    resources_requested = models.JSONField()

    #: Expiration date of the group
    expiration = models.DateTimeField(help_text="Expiration date of the group")


class HpcGroupChangeRequest(HpcGroupChangeRequestAbstract):
    """HpcGroupChangeRequest model"""

    #: Currently active version of the group change request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the group change request object"
    )


class HpcGroupChangeRequestVersion(HpcGroupChangeRequestAbstract):
    """HpcGroupChangeRequestVersion model"""

    #: Version number of the group change request object.
    version = models.IntegerField(help_text="Version number of this group change request object")


class HpcGroupCreateRequestAbstract(HpcGroupRequestAbstract):
    """HpcGroupCreateRequest abstract base class"""

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

    #: Description of what the group is working on.
    description = models.CharField(max_length=512, help_text="Description of the groups work")

    #: Expiration date of the group
    expiration = models.DateTimeField(help_text="Expiration date of the group")


class HpcGroupCreateRequest(HpcGroupCreateRequestAbstract):
    """HpcGroupCreateRequest model"""

    #: Currently active version of the group create request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the group create request object"
    )


class HpcGroupCreateRequestVersion(HpcGroupCreateRequestAbstract):
    """HpcGroupCreateRequestVersion model"""

    #: Version number of the group create request object.
    version = models.IntegerField(help_text="Version number of this group create request object")


class HpcGroupDeleteRequest(HpcGroupRequestAbstract):
    """HpcGroupDeleteRequest model"""

    #: Currently active version of the group delete request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the group delete request object"
    )


class HpcGroupDeleteRequestVersion(HpcGroupRequestAbstract):
    """HpcGroupDeleteRequestVersion model"""

    #: Version number of the group delete request object.
    version = models.IntegerField(help_text="Version number of this group delete request object")


class HpcUserRequestAbstract(HpcObjectAbstract):
    """HpcUserRequest abstract base class"""

    class Meta:
        abstract = True

    #: User creating the object.
    requester = models.ForeignKey(
        HpcUser,
        related_name="%(class)s",
        help_text="User creating the request",
        null=True,
        on_delete=models.SET_NULL,
    )

    #: Group the user belongs to.
    group = models.ForeignKey(
        HpcGroup,
        related_name="%(class)s",
        help_text="Group the request belongs to",
        on_delete=models.CASCADE,
    )

    #: Status of the request.
    status = models.CharField(
        max_length=16, choices=REQUEST_STATUS_CHOICES, help_text="Status of the request"
    )

    #: Comment for communication.
    comment = models.CharField(max_length=1024, help_text="Comment on request or revision")


class HpcUserChangeRequestAbstract(HpcUserRequestAbstract):
    """HpcUserChangeRequest abstract base class"""

    class Meta:
        abstract = True

    #: Users requested resources as JSON.
    resources_requested = models.JSONField()

    #: Expiration date of the user
    expiration = models.DateTimeField(help_text="Expiration date of the user")


class HpcUserChangeRequest(HpcUserChangeRequestAbstract):
    """HpcUserChangeRequest model"""

    #: Currently active version of the user change request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the user change request object"
    )


class HpcUserChangeRequestVersion(HpcUserChangeRequestAbstract):
    """HpcUserChangeRequestVersion model"""

    #: Version number of the user change request object.
    version = models.IntegerField(help_text="Version number of this user change request object")


class HpcUserCreateRequestAbstract(HpcUserRequestAbstract):
    """HpcUserCreateRequest abstract base class"""

    class Meta:
        abstract = True

    #: Users requested resources as JSON.
    resources_requested = models.JSONField()

    #: Expiration date of the user
    expiration = models.DateTimeField(help_text="Expiration date of the user")


class HpcUserCreateRequest(HpcUserCreateRequestAbstract):
    """HpcUserCreateRequest model"""

    #: Currently active version of the user create request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the user create request object"
    )


class HpcUserCreateRequestVersion(HpcUserCreateRequestAbstract):
    """HpcUserCreateRequestVersion model"""

    #: Version number of the user create request object.
    version = models.IntegerField(help_text="Version number of this user create request object")


class HpcUserDeleteRequest(HpcUserRequestAbstract):
    """HpcUserDeleteRequest model"""

    #: Currently active version of the user delete request object.
    current_version = models.IntegerField(
        help_text="Currently active version of the user delete request object"
    )


class HpcUserDeleteRequestVersion(HpcUserRequestAbstract):
    """HpcUserDeleteRequestVersion model"""

    #: Version number of the user delete request object.
    version = models.IntegerField(help_text="Version number of this user delete request object")


# Handlers


def handle_ldap_login(sender, user, **kwargs):
    """Signal for LDAP login handling"""

    if hasattr(user, "ldap_username"):

        # Make domain in username uppercase
        if user.username.find("@") != -1 and user.username.split("@")[1].islower():
            u_split = user.username.split("@")
            user.username = u_split[0] + "@" + u_split[1].upper()
            user.save()

        # Save user name from first_name and last_name into name
        if user.name in ["", None]:
            if user.first_name != "":
                user.name = user.first_name + (" " + user.last_name if user.last_name != "" else "")
                user.save()


user_logged_in.connect(handle_ldap_login)
