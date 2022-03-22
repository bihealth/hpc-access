from test_plus.test import TestCase

from usersec.models import (
    HpcGroup,
    HpcGroupVersion,
    HpcGroupChangeRequest,
    HpcGroupChangeRequestVersion,
    HpcGroupCreateRequest,
    HpcGroupCreateRequestVersion,
    HpcGroupDeleteRequest,
    HpcGroupDeleteRequestVersion,
    HpcUser,
    HpcUserVersion,
    HpcUserChangeRequest,
    HpcUserChangeRequestVersion,
    HpcUserCreateRequest,
    HpcUserCreateRequestVersion,
    HpcUserDeleteRequest,
    HpcUserDeleteRequestVersion,
    OBJECT_STATUS_DELETED,
    OBJECT_STATUS_INITIAL,
    REQUEST_STATUS_INITIAL,
    REQUEST_STATUS_RETRACTED,
    REQUEST_STATUS_DENIED,
)
from usersec.tests.factories import (
    HpcGroupChangeRequestFactory,
    HpcGroupCreateRequestFactory,
    HpcGroupDeleteRequestFactory,
    HpcGroupFactory,
    HpcUserChangeRequestFactory,
    HpcUserCreateRequestFactory,
    HpcUserDeleteRequestFactory,
    HpcUserFactory,
    hpc_obj_to_dict,
    hpc_version_obj_to_dict,
)


class CommentHistoryTesterMixin:
    """Mixin for testing comment history methods of request objects."""

    model = None
    version_model = None
    factory = None

    def _test_get_comment_history(self, comments):
        obj = self.factory(requester=self.user)
        history = [
            (
                self.user.username,
                obj.get_latest_version().date_created,
                obj.comment,
            )
        ]

        for comment in comments:
            obj.comment = comment
            obj = obj.save_with_version()

            if comment:
                history.append(
                    (
                        self.user.username,
                        obj.get_latest_version().date_created,
                        comment,
                    )
                )

        self.assertEqual(history, obj.get_comment_history())


class VersionTesterMixin:
    """Mixin for testing version-related methods."""

    model = None
    version_model = None
    factory = None

    def setUp(self):
        super().setUp()

        self.maxDiff = None
        self.user = self.make_user("user")

    def _test_create_with_version(self):
        self.assertFalse(self.model.objects.exists())
        self.assertFalse(self.version_model.objects.exists())

        # Factory calls create_with_version
        obj = self.factory()

        self.assertEqual(self.model.objects.count(), 1)
        self.assertEqual(self.version_model.objects.count(), 1)

        version_obj = self.version_model.objects.first()

        self.assertEqual(obj, version_obj.belongs_to)
        self.assertEqual(
            hpc_obj_to_dict(obj), hpc_version_obj_to_dict(version_obj)
        )

    def _test_create_with_version_two(self):
        obj1 = self.factory()
        obj2 = self.factory()

        self.assertEqual(self.model.objects.count(), 2)
        self.assertEqual(self.version_model.objects.count(), 2)

        version_obj1 = self.version_model.objects.first()
        version_obj2 = self.version_model.objects.last()

        self.assertEqual(obj1, version_obj1.belongs_to)
        self.assertEqual(
            hpc_obj_to_dict(obj1), hpc_version_obj_to_dict(version_obj1)
        )

        self.assertEqual(obj2, version_obj2.belongs_to)
        self.assertEqual(
            hpc_obj_to_dict(obj2), hpc_version_obj_to_dict(version_obj2)
        )

    def __assert_save_or_update_base(self, **update):
        self.assertEqual(self.model.objects.count(), 1)
        self.assertEqual(self.version_model.objects.count(), 2)

        obj = self.model.objects.first()
        version_objs = self.version_model.objects.all()

        self.assertEqual(version_objs[0].version, 1)
        self.assertEqual(version_objs[1].version, 2)
        self.assertEqual(obj.current_version, 2)

        version1_data = hpc_version_obj_to_dict(version_objs[0])
        version2_data = hpc_version_obj_to_dict(version_objs[1])
        data = hpc_obj_to_dict(obj)

        self.assertNotEqual(version1_data, version2_data)
        self.assertEqual(version2_data, data)

        for field, value in update.items():
            self.assertEqual(data[field], value)
            version1_data.pop(field)
            version2_data.pop(field)

        self.assertEqual(version1_data, version2_data)

    def _test_save_with_version_existing(self, **update):
        obj = self.factory()

        for k, v in update.items():
            setattr(obj, k, v)

        obj.save_with_version()
        self.__assert_save_or_update_base(**update)

    def _test_save_with_version_new(self, **supplementaries):
        obj = self.model()
        data = {
            k: v for k, v in vars(self.factory).items() if not k.startswith("_")
        }

        if supplementaries:
            data.update(supplementaries)

        for k, v in data.items():
            setattr(obj, k, v)

        obj.save_with_version()

        self.assertEqual(self.model.objects.count(), 1)
        self.assertEqual(self.version_model.objects.count(), 1)

        version_obj = self.version_model.objects.first()

        self.assertEqual(obj, version_obj.belongs_to)
        self.assertEqual(
            hpc_obj_to_dict(obj), hpc_version_obj_to_dict(version_obj)
        )

    def _test_update_with_version(self, **update):
        obj = self.factory()
        obj.update_with_version(**update)
        self.__assert_save_or_update_base(**update)

    def _test_delete_with_version(self):
        obj = self.factory()
        self.assertEqual(obj.status, OBJECT_STATUS_INITIAL)
        obj.delete_with_version()
        self.__assert_save_or_update_base(status=OBJECT_STATUS_DELETED)

    def _test_retract_with_version(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.retract_with_version()
        self.__assert_save_or_update_base(status=REQUEST_STATUS_RETRACTED)

    def _test_deny_with_version(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.deny_with_version()
        self.__assert_save_or_update_base(status=REQUEST_STATUS_DENIED)

    def _test_get_latest_version(self, **update):
        obj = self.factory()
        obj.update_with_version(**update)
        self.assertEqual(
            obj.get_latest_version(), self.version_model.objects.last()
        )

    def _test_get_latest_version_not_available(self):
        obj = self.model()
        self.assertIsNone(obj.get_latest_version())


class TestHpcUser(VersionTesterMixin, TestCase):
    """Tests for HpcUser model"""

    model = HpcUser
    version_model = HpcUserVersion
    factory = HpcUserFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        supplementaries = {
            "primary_group": HpcGroupFactory(),
            "username": "user_c",
        }
        self._test_save_with_version_new(**supplementaries)

    def test_save_with_version_existing(self):
        update = {"description": "description updated"}
        self._test_save_with_version_existing(**update)

    def test_update_with_version(self):
        update = {"description": "description updated"}
        self._test_update_with_version(**update)

    def test_delete_with_version(self):
        self._test_delete_with_version()

    def test_get_latest_version(self):
        update = {"description": "description updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()


class TestHpcGroup(VersionTesterMixin, TestCase):
    """Tests for HpcGroup model"""

    model = HpcGroup
    version_model = HpcGroupVersion
    factory = HpcGroupFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        supplementaries = {"name": "hpc-group"}
        self._test_save_with_version_new(**supplementaries)

    def test_save_with_version(self):
        update = {"description": "description updated"}
        self._test_save_with_version_existing(**update)

    def test_update_with_version(self):
        update = {"description": "description updated"}
        self._test_update_with_version(**update)

    def test_delete_with_version(self):
        self._test_delete_with_version()

    def test_get_latest_version(self):
        update = {"description": "description updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()


class TestHpcGroupChangeRequest(
    CommentHistoryTesterMixin, VersionTesterMixin, TestCase
):
    """Tests for HpcGroupChangeRequest model"""

    model = HpcGroupChangeRequest
    version_model = HpcGroupChangeRequestVersion
    factory = HpcGroupChangeRequestFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        self._test_save_with_version_new()

    def test_save_with_version(self):
        update = {"comment": "comment updated"}
        self._test_save_with_version_existing(**update)

    def test_update_with_version(self):
        update = {"comment": "comment updated"}
        self._test_update_with_version(**update)

    def test_retract_with_version(self):
        self._test_retract_with_version()

    def test_deny_with_version(self):
        self._test_deny_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)


class TestHpcGroupCreateRequest(
    CommentHistoryTesterMixin, VersionTesterMixin, TestCase
):
    """Tests for HpcGroupCreateRequest model"""

    model = HpcGroupCreateRequest
    version_model = HpcGroupCreateRequestVersion
    factory = HpcGroupCreateRequestFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        self._test_save_with_version_new()

    def test_save_with_version(self):
        update = {"comment": "comment updated"}
        self._test_save_with_version_existing(**update)

    def test_update_with_version(self):
        update = {"comment": "comment updated"}
        self._test_update_with_version(**update)

    def test_retract_with_version(self):
        self._test_retract_with_version()

    def test_deny_with_version(self):
        self._test_deny_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)


class TestHpcGroupDeleteRequest(
    CommentHistoryTesterMixin, VersionTesterMixin, TestCase
):
    """Tests for HpcGroupDeleteRequest model"""

    model = HpcGroupDeleteRequest
    version_model = HpcGroupDeleteRequestVersion
    factory = HpcGroupDeleteRequestFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        self._test_save_with_version_new()

    def test_save_with_version(self):
        update = {"comment": "comment updated"}
        self._test_save_with_version_existing(**update)

    def test_update_with_version(self):
        update = {"comment": "comment updated"}
        self._test_update_with_version(**update)

    def test_retract_with_version(self):
        self._test_retract_with_version()

    def test_deny_with_version(self):
        self._test_deny_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)


class TestHpcUserChangeRequest(
    CommentHistoryTesterMixin, VersionTesterMixin, TestCase
):
    """Tests for HpcUserChangeRequest model"""

    model = HpcUserChangeRequest
    version_model = HpcUserChangeRequestVersion
    factory = HpcUserChangeRequestFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        self._test_save_with_version_new()

    def test_save_with_version(self):
        update = {"comment": "comment updated"}
        self._test_save_with_version_existing(**update)

    def test_update_with_version(self):
        update = {"comment": "comment updated"}
        self._test_update_with_version(**update)

    def test_retract_with_version(self):
        self._test_retract_with_version()

    def test_deny_with_version(self):
        self._test_deny_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)


class TestHpcUserCreateRequest(
    CommentHistoryTesterMixin, VersionTesterMixin, TestCase
):
    """Tests for HpcUserCreateRequest model"""

    model = HpcUserCreateRequest
    version_model = HpcUserCreateRequestVersion
    factory = HpcUserCreateRequestFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        self._test_save_with_version_new()

    def test_save_with_version(self):
        update = {"comment": "comment updated"}
        self._test_save_with_version_existing(**update)

    def test_update_with_version(self):
        update = {"comment": "comment updated"}
        self._test_update_with_version(**update)

    def test_retract_with_version(self):
        self._test_retract_with_version()

    def test_deny_with_version(self):
        self._test_deny_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)


class TestHpcUserDeleteRequest(
    CommentHistoryTesterMixin, VersionTesterMixin, TestCase
):
    """Tests for HpcUserDeleteRequest model"""

    model = HpcUserDeleteRequest
    version_model = HpcUserDeleteRequestVersion
    factory = HpcUserDeleteRequestFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        self._test_save_with_version_new()

    def test_save_with_version(self):
        update = {"comment": "comment updated"}
        self._test_save_with_version_existing(**update)

    def test_update_with_version(self):
        update = {"comment": "comment updated"}
        self._test_update_with_version(**update)

    def test_retract_with_version(self):
        self._test_retract_with_version()

    def test_deny_with_version(self):
        self._test_deny_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)
