from freezegun import freeze_time
from snapshottest.django import TestCase as TestCaseSnap
from test_plus import TestCase as TestCasePlus

from hpcaccess.utils.tests import FROZEN_TIME
from usersec.serializers import (
    HpcGroupSerializer,
    HpcProjectSerializer,
    HpcUserSerializer,
)
from usersec.tests.factories import HpcGroupFactory, HpcProjectFactory, HpcUserFactory


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

    def testSerializeExisting(self):
        serializer = HpcUserSerializer(self.hpc_user)
        result = dict(serializer.data)
        result["uuid"] = "uuid_placeholder"
        result["primary_group"] = "primary_group_uuid_placeholder"
        self.assertMatchSnapshot(result)


@freeze_time(FROZEN_TIME)
class TestHpcGroupSerializer(ResetSequenceMixin, TestCaseSnap, TestCasePlus):
    def setUp(self):
        super().setUp()
        self.hpc_group = HpcGroupFactory()

    def testSerializeExisting(self):
        serializer = HpcGroupSerializer(self.hpc_group)
        result = dict(serializer.data)
        result["uuid"] = "uuid_placeholder"
        self.assertMatchSnapshot(result)


@freeze_time(FROZEN_TIME)
class TestHpcProjectSerializer(ResetSequenceMixin, TestCaseSnap, TestCasePlus):
    def setUp(self):
        super().setUp()
        self.hpc_group = HpcProjectFactory()

    def testSerializeExisting(self):
        serializer = HpcProjectSerializer(self.hpc_group)
        result = dict(serializer.data)
        result["uuid"] = "uuid_placeholder"
        result["group"] = "group_uuid_placeholder"
        self.assertMatchSnapshot(result)
