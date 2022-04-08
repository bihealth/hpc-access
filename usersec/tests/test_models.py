from django.conf import settings
from django.urls import reverse
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
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_REVISED,
    REQUEST_STATUS_REVISION,
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


class RequestTesterMixin:
    """Mixin for testing methods of request objects."""

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

    def _test_is_decided(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_DENIED)
        self.assertTrue(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_RETRACTED)
        self.assertFalse(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_APPROVED)
        self.assertTrue(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_ACTIVE)
        self.assertFalse(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_REVISED)
        self.assertFalse(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_REVISION)
        self.assertFalse(obj.is_decided())

    def _test_is_denied(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_DENIED)
        self.assertTrue(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_approved())
        self.assertFalse(obj.is_active())
        self.assertFalse(obj.is_revised())
        self.assertFalse(obj.is_revision())

    def _test_is_retracted(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_RETRACTED)
        self.assertTrue(obj.is_retracted())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_approved())
        self.assertFalse(obj.is_active())
        self.assertFalse(obj.is_revised())
        self.assertFalse(obj.is_revision())

    def _test_is_approved(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_APPROVED)
        self.assertTrue(obj.is_approved())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_active())
        self.assertFalse(obj.is_revised())
        self.assertFalse(obj.is_revision())

    def _test_is_active(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_ACTIVE)
        self.assertTrue(obj.is_active())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_approved())
        self.assertFalse(obj.is_revised())
        self.assertFalse(obj.is_revision())

    def _test_is_revised(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_REVISED)
        self.assertTrue(obj.is_revised())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_approved())
        self.assertTrue(obj.is_active())
        self.assertFalse(obj.is_revision())

    def _test_is_revision(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_REVISION)
        self.assertTrue(obj.is_revision())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_approved())
        self.assertFalse(obj.is_active())
        self.assertFalse(obj.is_revised())

    def _test_active(self):
        obj1 = self.factory(requester=self.user, status=REQUEST_STATUS_ACTIVE)
        obj2 = self.factory(requester=self.user, status=REQUEST_STATUS_REVISED)
        self.factory(requester=self.user, status=REQUEST_STATUS_REVISION)
        self.factory(requester=self.user, status=REQUEST_STATUS_RETRACTED)
        self.factory(requester=self.user, status=REQUEST_STATUS_DENIED)
        self.factory(requester=self.user, status=REQUEST_STATUS_APPROVED)
        self.assertEqual(list(self.model.objects.active()), [obj1, obj2])

    def _test_get_revision_url(self):
        obj = self.factory(requester=self.user)
        name = self.model.__name__.lower()
        expected = reverse("adminsec:{}-revision".format(name), kwargs={name: obj.uuid})
        self.assertEqual(obj.get_revision_url(), expected)

    def _test_get_approve_url(self):
        obj = self.factory(requester=self.user)
        name = self.model.__name__.lower()
        expected = reverse("adminsec:{}-approve".format(name), kwargs={name: obj.uuid})
        self.assertEqual(obj.get_approve_url(), expected)

    def _test_get_deny_url(self):
        obj = self.factory(requester=self.user)
        name = self.model.__name__.lower()
        expected = reverse("adminsec:{}-deny".format(name), kwargs={name: obj.uuid})
        self.assertEqual(obj.get_deny_url(), expected)

    def _test_get_update_url(self):
        obj = self.factory(requester=self.user)
        name = self.model.__name__.lower()
        expected = reverse("usersec:{}-update".format(name), kwargs={name: obj.uuid})
        self.assertEqual(obj.get_update_url(), expected)

    def _test_get_reactivate_url(self):
        obj = self.factory(requester=self.user)
        name = self.model.__name__.lower()
        expected = reverse("usersec:{}-reactivate".format(name), kwargs={name: obj.uuid})
        self.assertEqual(obj.get_reactivate_url(), expected)

    def _test_get_retract_url(self):
        obj = self.factory(requester=self.user)
        name = self.model.__name__.lower()
        expected = reverse("usersec:{}-retract".format(name), kwargs={name: obj.uuid})
        self.assertEqual(obj.get_retract_url(), expected)


class VersionTesterMixin:
    """Mixin for testing version-related methods."""

    model = None
    version_model = None
    factory = None

    def setUp(self):
        super().setUp()

        self.maxDiff = None
        self.user = self.make_user("user")
        self.hpcadmin = self.make_user("hpcadmin")
        self.hpcadmin.is_hpcadmin = True
        self.hpcadmin.save()

    def _test_create_with_version(self):
        self.assertFalse(self.model.objects.exists())
        self.assertFalse(self.version_model.objects.exists())

        # Factory calls create_with_version
        obj = self.factory()

        self.assertEqual(self.model.objects.count(), 1)
        self.assertEqual(self.version_model.objects.count(), 1)

        version_obj = self.version_model.objects.first()

        self.assertEqual(obj, version_obj.belongs_to)
        self.assertEqual(hpc_obj_to_dict(obj), hpc_version_obj_to_dict(version_obj))

    def _test_create_with_version_two(self):
        obj1 = self.factory()
        obj2 = self.factory()

        self.assertEqual(self.model.objects.count(), 2)
        self.assertEqual(self.version_model.objects.count(), 2)

        version_obj1 = self.version_model.objects.first()
        version_obj2 = self.version_model.objects.last()

        self.assertEqual(obj1, version_obj1.belongs_to)
        self.assertEqual(hpc_obj_to_dict(obj1), hpc_version_obj_to_dict(version_obj1))

        self.assertEqual(obj2, version_obj2.belongs_to)
        self.assertEqual(hpc_obj_to_dict(obj2), hpc_version_obj_to_dict(version_obj2))

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
        data = {k: v for k, v in vars(self.factory).items() if not k.startswith("_")}

        if supplementaries:
            data.update(supplementaries)

        for k, v in data.items():
            setattr(obj, k, v)

        obj.save_with_version()

        self.assertEqual(self.model.objects.count(), 1)
        self.assertEqual(self.version_model.objects.count(), 1)

        version_obj = self.version_model.objects.first()

        self.assertEqual(obj, version_obj.belongs_to)
        self.assertEqual(hpc_obj_to_dict(obj), hpc_version_obj_to_dict(version_obj))

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

    def _test_approve_with_version(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.approve_with_version()
        self.__assert_save_or_update_base(status=REQUEST_STATUS_APPROVED)

    def _test_revision_with_version(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.revision_with_version()
        self.__assert_save_or_update_base(status=REQUEST_STATUS_REVISION)

    def _test_revised_with_version(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.revised_with_version()
        self.__assert_save_or_update_base(status=REQUEST_STATUS_REVISED)

    def _test_get_latest_version(self, **update):
        obj = self.factory()
        obj.update_with_version(**update)
        self.assertEqual(obj.get_latest_version(), self.version_model.objects.last())

    def _test_get_latest_version_not_available(self):
        obj = self.model()
        self.assertIsNone(obj.get_latest_version())

    def _test_get_detail_url_user(self):
        obj = self.factory()
        name = self.model.__name__.lower()
        expected = reverse("usersec:{}-detail".format(name), kwargs={name: obj.uuid})
        self.assertEqual(obj.get_detail_url(self.user), expected)

    def _test_get_detail_url_admin(self):
        obj = self.factory()
        name = self.model.__name__.lower()
        expected = reverse("adminsec:{}-detail".format(name), kwargs={name: obj.uuid})
        self.assertEqual(obj.get_detail_url(self.hpcadmin), expected)


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
            "username": "user_" + settings.INSTITUTE_USERNAME_SUFFIX,
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

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()


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

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()


class TestHpcGroupChangeRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
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

    def test_approve_with_version(self):
        self._test_approve_with_version()

    def test_revision_with_version(self):
        self._test_revision_with_version()

    def test_revised_with_version(self):
        self._test_revised_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)

    def test_is_decided(self):
        self._test_is_decided()

    def test_is_denied(self):
        self._test_is_denied()

    def test_is_retracted(self):
        self._test_is_retracted()

    def test_is_approved(self):
        self._test_is_approved()

    def test_is_active(self):
        self._test_is_active()

    def test_is_revised(self):
        self._test_is_revised()

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_get_revision_url(self):
        self._test_get_revision_url()

    def test_get_approve_url(self):
        self._test_get_approve_url()

    def test_get_deny_url(self):
        self._test_get_deny_url()

    def test_get_update_url(self):
        self._test_get_update_url()

    def test_get_reactivate_url(self):
        self._test_get_reactivate_url()

    def test_get_retract_url(self):
        self._test_get_retract_url()


class TestHpcGroupCreateRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
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

    def test_approve_with_version(self):
        self._test_approve_with_version()

    def test_revision_with_version(self):
        self._test_revision_with_version()

    def test_revised_with_version(self):
        self._test_revised_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)

    def test_is_decided(self):
        self._test_is_decided()

    def test_is_denied(self):
        self._test_is_denied()

    def test_is_retracted(self):
        self._test_is_retracted()

    def test_is_approved(self):
        self._test_is_approved()

    def test_is_active(self):
        self._test_is_active()

    def test_is_revised(self):
        self._test_is_revised()

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_get_revision_url(self):
        self._test_get_revision_url()

    def test_get_approve_url(self):
        self._test_get_approve_url()

    def test_get_deny_url(self):
        self._test_get_deny_url()

    def test_get_update_url(self):
        self._test_get_update_url()

    def test_get_reactivate_url(self):
        self._test_get_reactivate_url()

    def test_get_retract_url(self):
        self._test_get_retract_url()


class TestHpcGroupDeleteRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
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

    def test_approve_with_version(self):
        self._test_approve_with_version()

    def test_revision_with_version(self):
        self._test_revision_with_version()

    def test_revised_with_version(self):
        self._test_revised_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)

    def test_is_decided(self):
        self._test_is_decided()

    def test_is_denied(self):
        self._test_is_denied()

    def test_is_retracted(self):
        self._test_is_retracted()

    def test_is_approved(self):
        self._test_is_approved()

    def test_is_active(self):
        self._test_is_active()

    def test_is_revised(self):
        self._test_is_revised()

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_get_revision_url(self):
        self._test_get_revision_url()

    def test_get_approve_url(self):
        self._test_get_approve_url()

    def test_get_deny_url(self):
        self._test_get_deny_url()

    def test_get_update_url(self):
        self._test_get_update_url()

    def test_get_reactivate_url(self):
        self._test_get_reactivate_url()

    def test_get_retract_url(self):
        self._test_get_retract_url()


class TestHpcUserChangeRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
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

    def test_approve_with_version(self):
        self._test_approve_with_version()

    def test_revision_with_version(self):
        self._test_revision_with_version()

    def test_revised_with_version(self):
        self._test_revised_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)

    def test_is_decided(self):
        self._test_is_decided()

    def test_is_denied(self):
        self._test_is_denied()

    def test_is_retracted(self):
        self._test_is_retracted()

    def test_is_approved(self):
        self._test_is_approved()

    def test_is_active(self):
        self._test_is_active()

    def test_is_revised(self):
        self._test_is_revised()

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_get_revision_url(self):
        self._test_get_revision_url()

    def test_get_approve_url(self):
        self._test_get_approve_url()

    def test_get_deny_url(self):
        self._test_get_deny_url()

    def test_get_update_url(self):
        self._test_get_update_url()

    def test_get_reactivate_url(self):
        self._test_get_reactivate_url()

    def test_get_retract_url(self):
        self._test_get_retract_url()


class TestHpcUserCreateRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
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

    def test_approve_with_version(self):
        self._test_approve_with_version()

    def test_revision_with_version(self):
        self._test_revision_with_version()

    def test_revised_with_version(self):
        self._test_revised_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)

    def test_is_decided(self):
        self._test_is_decided()

    def test_is_denied(self):
        self._test_is_denied()

    def test_is_retracted(self):
        self._test_is_retracted()

    def test_is_approved(self):
        self._test_is_approved()

    def test_is_active(self):
        self._test_is_active()

    def test_is_revised(self):
        self._test_is_revised()

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_get_revision_url(self):
        self._test_get_revision_url()

    def test_get_approve_url(self):
        self._test_get_approve_url()

    def test_get_deny_url(self):
        self._test_get_deny_url()

    def test_get_update_url(self):
        self._test_get_update_url()

    def test_get_reactivate_url(self):
        self._test_get_reactivate_url()

    def test_get_retract_url(self):
        self._test_get_retract_url()


class TestHpcUserDeleteRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
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

    def test_approve_with_version(self):
        self._test_approve_with_version()

    def test_revision_with_version(self):
        self._test_revision_with_version()

    def test_revised_with_version(self):
        self._test_revised_with_version()

    def test_get_latest_version(self):
        update = {"comment": "comment updated"}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)

    def test_is_decided(self):
        self._test_is_decided()

    def test_is_denied(self):
        self._test_is_denied()

    def test_is_retracted(self):
        self._test_is_retracted()

    def test_is_approved(self):
        self._test_is_approved()

    def test_is_active(self):
        self._test_is_active()

    def test_is_revised(self):
        self._test_is_revised()

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_get_revision_url(self):
        self._test_get_revision_url()

    def test_get_approve_url(self):
        self._test_get_approve_url()

    def test_get_deny_url(self):
        self._test_get_deny_url()

    def test_get_update_url(self):
        self._test_get_update_url()

    def test_get_reactivate_url(self):
        self._test_get_reactivate_url()

    def test_get_retract_url(self):
        self._test_get_retract_url()
