from freezegun import freeze_time
from snapshottest.django import TestCase as TestCaseSnap
from test_plus import TestCase as TestCasePlus

from hpcaccess.utils.tests import FROZEN_TIME
from usersec.serializers import (
    HpcGroupCreateRequestSerializer,
    HpcGroupSerializer,
    HpcProjectCreateRequestSerializer,
    HpcProjectSerializer,
    HpcUserSerializer,
)
from usersec.tests.factories import (
    HpcGroupCreateRequestFactory,
    HpcGroupFactory,
    HpcProjectCreateRequestFactory,
    HpcProjectFactory,
    HpcUserFactory,
)


class ResetSequenceMixin:
    def setUp(self):
        super().setUp()
        HpcUserFactory.reset_sequence()
        HpcGroupFactory.reset_sequence()
        HpcProjectFactory.reset_sequence()


@freeze_time(FROZEN_TIME)
class TestHpcUserSerializer(ResetSequenceMixin, TestCaseSnap, TestCasePlus):
    def setUp(self):
        super().setUp()
        self.hpc_user = HpcUserFactory()

    def testSerializerExisting(self):
        serializer = HpcUserSerializer(self.hpc_user)
        result = dict(serializer.data)
        result["uuid"] = "uuid_placeholder"
        result["email"] = "email_placeholder"
        result["primary_group"] = "primary_group_uuid_placeholder"
        result["phone_number"] = "phone_number_placeholder"
        result["full_name"] = "name_placeholder"
        result["first_name"] = "first_name_placeholder"
        result["last_name"] = "last_name_placeholder"
        self.assertMatchSnapshot(result)


@freeze_time(FROZEN_TIME)
class TestHpcGroupSerializer(ResetSequenceMixin, TestCaseSnap, TestCasePlus):
    def setUp(self):
        super().setUp()
        self.hpc_group = HpcGroupFactory()
        self.maxDiff = None

    def testSerializerExisting(self):
        serializer = HpcGroupSerializer(self.hpc_group)
        result = dict(serializer.data)
        result["uuid"] = "uuid_placeholder"
        self.assertMatchSnapshot(result)


@freeze_time(FROZEN_TIME)
class TestHpcProjectSerializer(ResetSequenceMixin, TestCaseSnap, TestCasePlus):
    def setUp(self):
        super().setUp()
        self.hpc_project = HpcProjectFactory()
        self.maxDiff = None

    def testSerializerExisting(self):
        serializer = HpcProjectSerializer(self.hpc_project)
        result = dict(serializer.data)
        result["uuid"] = "uuid_placeholder"
        result["group"] = "group_uuid_placeholder"
        self.assertMatchSnapshot(result)


@freeze_time(FROZEN_TIME)
class TestHpcGroupCreateRequestSerializer(ResetSequenceMixin, TestCaseSnap, TestCasePlus):
    def setUp(self):
        super().setUp()
        self.hpc_group_create_request = HpcGroupCreateRequestFactory()
        self.maxDiff = None

    def testSerializerExisting(self):
        serializer = HpcGroupCreateRequestSerializer(self.hpc_group_create_request)
        result = dict(serializer.data)
        result["uuid"] = "uuid_placeholder"
        self.assertMatchSnapshot(result)


@freeze_time(FROZEN_TIME)
class TestHpcProjectCreateRequestSerializer(ResetSequenceMixin, TestCaseSnap, TestCasePlus):
    def setUp(self):
        super().setUp()
        self.hpc_project_create_request = HpcProjectCreateRequestFactory()
        self.maxDiff = None

    def testSerializerExisting(self):
        serializer = HpcProjectCreateRequestSerializer(self.hpc_project_create_request)
        result = dict(serializer.data)
        result["uuid"] = "uuid_placeholder"
        result["group"] = "group_uuid_placeholder"
        result["name_requested"] = "name_requested_placeholder"
        self.assertMatchSnapshot(result)
