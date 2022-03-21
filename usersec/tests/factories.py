import json
from datetime import datetime

import factory
from django.forms import model_to_dict
from django.utils.timezone import utc

from usersec.models import (
    HpcUser,
    HpcGroup,
    HpcGroupChangeRequest,
    HpcGroupCreateRequest,
    HpcGroupDeleteRequest,
    HpcUserCreateRequest,
    HpcUserChangeRequest,
    HpcUserDeleteRequest,
    OBJECT_STATUS_ACTIVE,
    REQUEST_STATUS_INITIAL,
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
HPCGROUPCREATEREQUESTFORM_DATA_VALID = {
    "resources_requested": json.dumps({"resource": 100}),
    "description": "some group description",
    "expiration": "2022-01-01",
    "comment": "nothing",
    "current_version": 1,
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


class HpcGroupFactory(HpcObjectFactoryBase):
    """Factory for HpcGroup model"""

    class Meta:
        model = HpcGroup

    owner = None  # HpcUser
    delegate = None  # HpcUser
    resources_requested = {"null": "null"}
    resources_used = {"null": "null"}
    description = "this is a group"
    creator = None  # User
    status = OBJECT_STATUS_ACTIVE
    gid = 2000
    name = factory.Sequence(lambda n: f"hpc-group{n}")
    folder = "/data/group"
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcUserFactory(HpcObjectFactoryBase):
    """Factory for HpcUser model"""

    class Meta:
        model = HpcUser

    user = None  # User
    primary_group = factory.SubFactory(HpcGroupFactory)
    resources_requested = {"null": "null"}
    resources_used = {"null": "null"}
    creator = None  # User
    status = OBJECT_STATUS_ACTIVE
    description = "this is a user"
    uid = 2000
    username = factory.Sequence(lambda n: f"user{n}_c")
    first_names = "Test"
    surname = "User"
    email = "user@test.org"
    phone = "+123456"
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcRequestFactoryBase(HpcObjectFactoryBase):
    """Base class for HpcRequest factories"""

    class Meta:
        abstract = True

    requester = None  # User
    status = REQUEST_STATUS_INITIAL
    comment = "some comment"


class HpcGroupRequestFactoryBase(HpcRequestFactoryBase):
    """Base class for HpcGroupRequest factories"""

    class Meta:
        abstract = True

    group = None  # HpcGroup


class HpcGroupChangeRequestFactory(HpcGroupRequestFactoryBase):
    """Factory for HpcGroupChangeRequest model"""

    class Meta:
        model = HpcGroupChangeRequest

    resources_requested = {"null": "null"}
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcGroupCreateRequestFactory(HpcGroupRequestFactoryBase):
    """Factory for HpcGroupCreateRequest model"""

    class Meta:
        model = HpcGroupCreateRequest

    resources_requested = {"null": "null"}
    description = "some group create request"
    expiration = datetime(2050, 1, 1, tzinfo=utc)
    requester = None  # User


class HpcGroupDeleteRequestFactory(HpcGroupRequestFactoryBase):
    """Factory for HpcGroupDeleteRequest model"""

    class Meta:
        model = HpcGroupDeleteRequest


class HpcUserRequestFactoryBase(HpcRequestFactoryBase):
    """Base class for HpcUserRequest factories"""

    class Meta:
        abstract = True

    user = None  # HpcUser


class HpcUserChangeRequestFactory(HpcUserRequestFactoryBase):
    """Factory for HpcUserChangeRequest model"""

    class Meta:
        model = HpcUserChangeRequest

    resources_requested = {"null": "null"}
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcUserCreateRequestFactory(HpcUserRequestFactoryBase):
    """Factory for HpcUserCreateRequest model"""

    class Meta:
        model = HpcUserCreateRequest

    resources_requested = {"null": "null"}
    expiration = datetime(2050, 1, 1, tzinfo=utc)


class HpcUserDeleteRequestFactory(HpcUserRequestFactoryBase):
    """Factory for HpcUserDeleteRequest model"""

    class Meta:
        model = HpcUserDeleteRequest
