from datetime import datetime
import json

from django.conf import settings
from django.forms import model_to_dict
from django.utils.timezone import utc
import factory

from usersec.models import (
    HpcGroup,
    HpcGroupChangeRequest,
    HpcGroupCreateRequest,
    HpcGroupDeleteRequest,
    HpcGroupInvitation,
    HpcProject,
    HpcProjectChangeRequest,
    HpcProjectCreateRequest,
    HpcProjectDeleteRequest,
    HpcProjectInvitation,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
    HpcUserDeleteRequest,
)

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


def hpc_version_obj_to_dict(obj):
    return model_to_dict(obj, exclude=["id", "uuid", "version", "belongs_to"])


def hpc_obj_to_dict(obj):
    return model_to_dict(obj, exclude=["id", "uuid", "current_version"])


# ------------------------------------------------------------------------------
# Form data
# ------------------------------------------------------------------------------


#: Valid data for HpcGroupCreateRequestForm.
HPCGROUPCREATEREQUEST_FORM_DATA_VALID = {
    "resources_requested": json.dumps({"resource": 100}),
    "tier1": 100,
    "tier2": 200,
    "description": "some group description",
    "expiration": "2022-01-01",
    "comment": "nothing",
}


#: Valid data for HpcGroupChangeRequestForm.
HPCGROUPCHANGEREQUEST_FORM_DATA_VALID = {
    "resources_requested": json.dumps({"resource": 111}),
    "tier1": 111,
    "tier2": 222,
    "description": "updated group description",
    "expiration": "2023-01-01",
    "comment": "nothing",
}


#: Valid data for HpcUserCreateRequestForm.
HPCUSERCREATEREQUEST_FORM_DATA_VALID = {
    "resources_requested": json.dumps({"resource": 100}),
    "tier1": 100,
    "tier2": 200,
    "email": "user@" + settings.INSTITUTE_EMAIL_DOMAINS.split(",")[0],
    "expiration": "2022-01-01",
    "comment": "nothing",
}


#: Valid data for HpcUserChangeRequestForm.
HPCUSERCHANGEREQUEST_FORM_DATA_VALID = {
    "expiration": "2022-01-01",
    "comment": "nothing",
}


#: Valid data for HpcProjectCreateRequestForm.
HPCPROJECTCREATEREQUEST_FORM_DATA_VALID = {
    "resources_requested": json.dumps({"resource": 100}),
    "tier1": 100,
    "tier2": 200,
    "description": "some project description",
    "name": "some-project",
    "expiration": "2022-01-01",
    "comment": "nothing",
    "members": None,  # fill out before usage
}


#: Valid data for HpcProjectCreateRequestForm.
HPCPROJECTCHANGEREQUEST_FORM_DATA_VALID = {
    "resources_requested": json.dumps({"resource": 111}),
    "tier1": 111,
    "tier2": 222,
    "description": "updated project description",
    "expiration": "2022-01-01",
    "comment": "nothing",
    "members": None,  # fill out before usage
}


# ------------------------------------------------------------------------------
# Factories
# ------------------------------------------------------------------------------


class HpcObjectFactoryBase(factory.django.DjangoModelFactory):
    """Base factory class for every Hpc object factory"""

    class Meta:
        abstract = True

    current_version = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default ``_create`` with custom call."""
        manager = cls._get_manager(model_class)
        # The default would use ``manager.create(*args, **kwargs)``
        return manager.create_with_version(*args, **kwargs)


class HpcRequestFactoryBase(HpcObjectFactoryBase):
    """Base class for HpcRequest factories"""

    class Meta:
        abstract = True

    requester = None  # User
    editor = factory.LazyAttribute(lambda o: o.requester)
    comment = "some comment"


# HpcGroup related
# ------------------------------------------------------------------------------


class HpcGroupFactory(HpcObjectFactoryBase):
    """Factory for HpcGroup model"""

    class Meta:
        model = HpcGroup

    owner = None  # HpcUser
    delegate = None  # HpcUser
    resources_requested = {"tier1": 1, "tier2": 0}
    resources_used = {"tier1": 0.5, "tier2": 0}
    description = "this is a group"
    creator = None  # User
    gid = 2000
    name = factory.Sequence(lambda n: f"hpc-group{n}")
    folder = "/data/group"
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcGroupRequestFactoryBase(HpcRequestFactoryBase):
    """Base class for HpcGroupRequest factories"""

    class Meta:
        abstract = True

    group = None  # HpcGroup


class HpcGroupCreateRequestFactory(HpcGroupRequestFactoryBase):
    """Factory for HpcGroupCreateRequest model"""

    class Meta:
        model = HpcGroupCreateRequest

    resources_requested = {"null": "null"}
    description = "some group create request"
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcGroupChangeRequestFactory(HpcGroupRequestFactoryBase):
    """Factory for HpcGroupChangeRequest model"""

    class Meta:
        model = HpcGroupChangeRequest

    resources_requested = {"null": "null"}
    description = "updated group description"
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcGroupDeleteRequestFactory(HpcGroupRequestFactoryBase):
    """Factory for HpcGroupDeleteRequest model"""

    class Meta:
        model = HpcGroupDeleteRequest


# HpcUser related
# ------------------------------------------------------------------------------


class HpcUserFactory(HpcObjectFactoryBase):
    """Factory for HpcUser model"""

    class Meta:
        model = HpcUser

    user = None  # User
    primary_group = factory.SubFactory(HpcGroupFactory)
    resources_requested = {"null": "null"}
    resources_used = {"null": "null"}
    creator = None  # User
    description = "this is a user"
    uid = 2000
    username = factory.Sequence(lambda n: f"user{n}_" + settings.INSTITUTE_USERNAME_SUFFIX)
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcUserRequestFactoryBase(HpcRequestFactoryBase):
    """Base class for HpcUserRequest factories"""

    class Meta:
        abstract = True

    user = None  # HpcUser


class HpcUserCreateRequestFactory(HpcUserRequestFactoryBase):
    """Factory for HpcUserCreateRequest model"""

    class Meta:
        model = HpcUserCreateRequest

    group = None
    email = "user@" + settings.INSTITUTE_EMAIL_DOMAINS.split(",")[0]
    resources_requested = {"null": "null"}
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcUserChangeRequestFactory(HpcUserRequestFactoryBase):
    """Factory for HpcUserChangeRequest model"""

    class Meta:
        model = HpcUserChangeRequest

    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcUserDeleteRequestFactory(HpcUserRequestFactoryBase):
    """Factory for HpcUserDeleteRequest model"""

    class Meta:
        model = HpcUserDeleteRequest


# HpcProject related
# ------------------------------------------------------------------------------


class HpcProjectFactory(HpcObjectFactoryBase):
    """Factory for HpcProject model"""

    class Meta:
        model = HpcProject

    group = factory.SubFactory(HpcGroupFactory)
    resources_requested = {"null": "null"}
    resources_used = {"null": "null"}
    creator = None  # User
    delegate = None  # HpcUser
    description = "this is a project"
    gid = 5000
    name = factory.Sequence(lambda n: f"hpc-project{n}")
    folder = "/data/project"
    # members = None  # List of HpcUsers
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcProjectRequestFactoryBase(HpcRequestFactoryBase):
    """Base class for HpcProjectRequest factories"""

    class Meta:
        abstract = True

    project = None  # HpcProject


class HpcProjectCreateRequestFactory(HpcProjectRequestFactoryBase):
    """Factory for HpcProjectCreateRequest model"""

    class Meta:
        model = HpcProjectCreateRequest

    group = factory.SubFactory(HpcGroupFactory)
    delegate = None
    resources_requested = {"null": "null"}
    description = "some description"
    name = factory.Sequence(lambda n: f"hpc-project100{n}")
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcProjectChangeRequestFactory(HpcProjectRequestFactoryBase):
    """Factory for HpcProjectChangeRequest model"""

    class Meta:
        model = HpcProjectChangeRequest

    resources_requested = {"null": "null"}
    delegate = None
    description = "updated description"
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcProjectDeleteRequestFactory(HpcProjectRequestFactoryBase):
    """Factory for HpcProjectDeleteRequest model"""

    class Meta:
        model = HpcProjectDeleteRequest


class HpcProjectInvitationFactory(HpcObjectFactoryBase):
    """Factory for HpcProjectInvitation model"""

    class Meta:
        model = HpcProjectInvitation

    project = factory.SubFactory(HpcProjectFactory)
    hpcprojectcreaterequest = factory.SubFactory(HpcProjectCreateRequestFactory)
    user = factory.SubFactory(HpcUserFactory)


class HpcGroupInvitationFactory(HpcObjectFactoryBase):
    """Factory for HpcGroupInvitation model"""

    class Meta:
        model = HpcGroupInvitation

    hpcusercreaterequest = factory.SubFactory(HpcUserCreateRequestFactory)
    username = factory.Sequence(lambda n: f"user{n}_" + settings.INSTITUTE_USERNAME_SUFFIX)
