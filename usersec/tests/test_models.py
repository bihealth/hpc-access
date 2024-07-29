from django.conf import settings
from django.urls import reverse
from factory import LazyAttribute, SubFactory
from test_plus.test import TestCase

from adminsec.constants import TIER_USER_HOME
from usersec.models import (
    INVITATION_STATUS_ACCEPTED,
    INVITATION_STATUS_PENDING,
    INVITATION_STATUS_REJECTED,
    OBJECT_STATUS_DELETED,
    OBJECT_STATUS_INITIAL,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_DENIED,
    REQUEST_STATUS_INITIAL,
    REQUEST_STATUS_RETRACTED,
    REQUEST_STATUS_REVISED,
    REQUEST_STATUS_REVISION,
    TERMS_AUDIENCE_ALL,
    HpcGroup,
    HpcGroupChangeRequest,
    HpcGroupChangeRequestVersion,
    HpcGroupCreateRequest,
    HpcGroupCreateRequestVersion,
    HpcGroupDeleteRequest,
    HpcGroupDeleteRequestVersion,
    HpcGroupInvitation,
    HpcGroupInvitationVersion,
    HpcGroupVersion,
    HpcProject,
    HpcProjectChangeRequest,
    HpcProjectChangeRequestVersion,
    HpcProjectCreateRequest,
    HpcProjectCreateRequestVersion,
    HpcProjectDeleteRequest,
    HpcProjectDeleteRequestVersion,
    HpcProjectInvitation,
    HpcProjectInvitationVersion,
    HpcProjectVersion,
    HpcQuotaStatus,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserChangeRequestVersion,
    HpcUserCreateRequest,
    HpcUserCreateRequestVersion,
    HpcUserDeleteRequest,
    HpcUserDeleteRequestVersion,
    HpcUserVersion,
    TermsAndConditions,
    parse_email,
    user_active,
)
from usersec.tests.factories import (
    HpcGroupChangeRequestFactory,
    HpcGroupCreateRequestFactory,
    HpcGroupDeleteRequestFactory,
    HpcGroupFactory,
    HpcGroupInvitationFactory,
    HpcProjectChangeRequestFactory,
    HpcProjectCreateRequestFactory,
    HpcProjectDeleteRequestFactory,
    HpcProjectFactory,
    HpcProjectInvitationFactory,
    HpcUserChangeRequestFactory,
    HpcUserCreateRequestFactory,
    HpcUserDeleteRequestFactory,
    HpcUserFactory,
    TermsAndConditionsFactory,
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

    def _test_display_status(self):
        data = {
            REQUEST_STATUS_INITIAL: "initial",
            REQUEST_STATUS_ACTIVE: "pending",
            REQUEST_STATUS_REVISION: "revision required",
            REQUEST_STATUS_REVISED: "pending (revised)",
            REQUEST_STATUS_APPROVED: "approved",
            REQUEST_STATUS_DENIED: "denied",
            REQUEST_STATUS_RETRACTED: "retracted",
        }

        for key, value in data.items():
            obj = self.factory(requester=self.user, status=key)
            self.assertEqual(obj.display_status(), value)

        obj = self.factory(requester=self.user, status="???")
        self.assertEqual(obj.display_status(), "unknown status")


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

        obj.refresh_from_db()
        version_obj = self.version_model.objects.get(belongs_to=obj)

        self.assertEqual(hpc_obj_to_dict(obj), hpc_version_obj_to_dict(version_obj))

    def _test_create_with_version_two(self):
        obj1 = self.factory()
        obj2 = self.factory()

        self.assertEqual(self.model.objects.count(), 2)
        self.assertEqual(self.version_model.objects.count(), 2)

        version_obj1 = self.version_model.objects.get(belongs_to=obj1)
        version_obj2 = self.version_model.objects.get(belongs_to=obj2)

        obj1.refresh_from_db()
        obj2.refresh_from_db()

        self.assertEqual(hpc_obj_to_dict(obj1), hpc_version_obj_to_dict(version_obj1))
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
            if not isinstance(v, SubFactory) and not isinstance(v, LazyAttribute):
                setattr(obj, k, v)

        obj.save_with_version()
        obj.refresh_from_db()

        self.assertEqual(self.model.objects.count(), 1)
        self.assertEqual(self.version_model.objects.count(), 1)

        version_obj = self.version_model.objects.get(belongs_to=obj)

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

    def test_get_pending_invitations(self):
        user = self.factory()
        HpcProjectInvitationFactory(user=user, status=INVITATION_STATUS_PENDING)
        HpcProjectInvitationFactory(user=user, status=INVITATION_STATUS_ACCEPTED)
        HpcProjectInvitationFactory(user=user, status=INVITATION_STATUS_REJECTED)
        self.assertEqual(
            list(HpcProjectInvitation.objects.filter(user=user, status=INVITATION_STATUS_PENDING)),
            list(user.get_pending_invitations()),
        )

    def test_generate_quota_report_green(self):
        user = self.factory(
            resources_requested={TIER_USER_HOME: 20},
            resources_used={TIER_USER_HOME: 10},
            home_directory="/home/users",
        )
        expected = {
            "used": {TIER_USER_HOME: 10},
            "requested": {TIER_USER_HOME: 20},
            "percentage": {TIER_USER_HOME: 50},
            "status": {TIER_USER_HOME: HpcQuotaStatus.GREEN},
            "folders": {TIER_USER_HOME: "/home/users"},
            "warnings": [],
        }

        self.assertDictEqual(user.generate_quota_report(), expected)

    def test_generate_quota_report_yellow(self):
        user = self.factory(
            resources_requested={TIER_USER_HOME: 20},
            resources_used={TIER_USER_HOME: 18},
            home_directory="/home/users",
        )
        expected = {
            "used": {TIER_USER_HOME: 18},
            "requested": {TIER_USER_HOME: 20},
            "percentage": {TIER_USER_HOME: 90},
            "status": {TIER_USER_HOME: HpcQuotaStatus.YELLOW},
            "folders": {TIER_USER_HOME: "/home/users"},
            "warnings": [],
        }

        self.assertDictEqual(user.generate_quota_report(), expected)

    def test_generate_quota_report_red(self):
        user = self.factory(
            resources_requested={TIER_USER_HOME: 20},
            resources_used={TIER_USER_HOME: 20},
            home_directory="/home/users",
        )
        expected = {
            "used": {TIER_USER_HOME: 20},
            "requested": {TIER_USER_HOME: 20},
            "percentage": {TIER_USER_HOME: 100},
            "status": {TIER_USER_HOME: HpcQuotaStatus.RED},
            "folders": {TIER_USER_HOME: "/home/users"},
            "warnings": [],
        }

        self.assertDictEqual(user.generate_quota_report(), expected)

    def test_parse_email(self):
        email = parse_email("valid@example.com")
        self.assertEqual(email, "valid@example.com")

    def test_parse_email_invalid(self):
        with self.assertRaisesRegex(ValueError, "Email is not valid"):
            parse_email("invalid")

    def test_parse_email_empty(self):
        with self.assertRaisesRegex(ValueError, "Email is empty"):
            parse_email("")

    def test_user_active(self):
        hpcuser = self.factory(user=self.user)
        self.assertTrue(user_active(hpcuser))

    def test_user_inactive_disabled(self):
        self.user.is_active = False
        self.user.save()
        hpcuser = self.factory(user=self.user)
        self.assertFalse(user_active(hpcuser))

    def test_user_inactive_expired(self):
        hpcuser = self.factory(user=self.user, status="EXPIRED")
        self.assertFalse(user_active(hpcuser))

    def test_user_inactive_nologin(self):
        hpcuser = self.factory(user=self.user, login_shell="/usr/sbin/nologin")
        self.assertFalse(user_active(hpcuser))

    def test_get_user_email(self):
        user = self.factory()
        self.assertEqual(user.get_user_email(), user.user.email)

    def test_get_user_email_inactive(self):
        user = self.factory()
        user.user.is_active = False
        user.user.save()
        self.assertIsNone(user.get_user_email())

    def test_get_user_active(self):
        user = self.factory()
        self.assertTrue(user.get_user_active())

    def test_get_manager_active(self):
        with self.assertRaisesRegex(
            NotImplementedError, "Method only implemented for Hpc{Group,Project} objects"
        ):
            self.factory().get_manager_active()

    def test_get_manager_emails(self):
        with self.assertRaisesRegex(
            NotImplementedError, "Method only implemented for Hpc{Group,Project} objects"
        ):
            self.factory().get_manager_emails()

    def test_get_manager_contact(self):
        with self.assertRaisesRegex(
            NotImplementedError, "Method only implemented for Hpc{Group,Project} objects"
        ):
            self.factory().get_manager_contact()


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

    def test_generate_quota_report(self):
        obj = self.factory(
            resources_requested={
                "storage_green": 20,
                "storage_yellow": 20,
                "storage_red": 20,
                "storage_requested_only": 20,
            },
            resources_used={
                "storage_green": 10,
                "storage_yellow": 18,
                "storage_red": 20,
                "storage_used_only": 20,
            },
            folders={
                "storage_green": "/home/groups/green",
                "storage_yellow": "/home/groups/yellow",
                "storage_red": "/home/groups/red",
            },
        )
        expected = {
            "used": {
                "storage_green": 10,
                "storage_yellow": 18,
                "storage_red": 20,
            },
            "requested": {
                "storage_green": 20,
                "storage_yellow": 20,
                "storage_red": 20,
            },
            "percentage": {
                "storage_green": 50,
                "storage_yellow": 90,
                "storage_red": 100,
            },
            "status": {
                "storage_green": HpcQuotaStatus.GREEN,
                "storage_yellow": HpcQuotaStatus.YELLOW,
                "storage_red": HpcQuotaStatus.RED,
            },
            "folders": {
                "storage_green": "/home/groups/green",
                "storage_yellow": "/home/groups/yellow",
                "storage_red": "/home/groups/red",
            },
            "warnings": [
                "Resource storage_used_only is used, but not found in requested resources",
                "Resource storage_requested_only is requested, but not found in used resources",
            ],
        }
        self.assertDictEqual(obj.generate_quota_report(), expected)

    def test_get_manager_emails(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_emails(), {"delegate": "delegate@example.com"})

    def test_get_manager_emails_no_delegate(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        obj = self.factory(owner=hpcuser_owner)
        self.assertEqual(obj.get_manager_emails(), {"owner": "owner@example.com"})

    def test_get_manager_emails_slim_false(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_emails(slim=False),
            {"owner": "owner@example.com", "delegate": "delegate@example.com"},
        )

    def test_get_manager_emails_invalid_address(self):
        user_owner = self.make_user("owner")
        user_owner.email = "INVALID"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        obj = self.factory(owner=hpcuser_owner)
        self.assertEqual(obj.get_manager_emails(), {})

    def test_get_manager_names(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_names(), {"delegate": "Delegate"})

    def test_get_manager_names_no_delegate(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        obj = self.factory(owner=hpcuser_owner)
        self.assertEqual(obj.get_manager_names(), {"owner": "Owner"})

    def test_get_manager_names_slim_false(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_names(slim=False), {"owner": "Owner", "delegate": "Delegate"}
        )

    def test_get_manager_contact(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_contact(),
            {"delegate": {"name": "Delegate", "email": "delegate@example.com"}},
        )

    def test_get_manager_contact_slim_false(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_contact(slim=False),
            {
                "owner": {"name": "Owner", "email": "owner@example.com"},
                "delegate": {"name": "Delegate", "email": "delegate@example.com"},
            },
        )

    def test_get_manager_contact_invalid_address(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.email = "INVALID"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_contact(slim=False),
            {
                "owner": {"name": "Owner", "email": "owner@example.com"},
            },
        )

    def test_get_manager_active(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_active(), ["delegate"])

    def test_get_manager_active_no_delegate(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        obj = self.factory(owner=hpcuser_owner)
        self.assertEqual(obj.get_manager_active(), ["owner"])

    def test_get_manager_active_slim_false(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_active(slim=False), ["delegate", "owner"])

    def test_get_manager_active_delegate_inactive(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate, status="EXPIRED")
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_active(), ["owner"])

    def test_get_manager_active_all_inactive(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner, status="EXPIRED")
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate, status="EXPIRED")
        obj = self.factory(owner=hpcuser_owner, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_active(), [])

    def test_get_user_email(self):
        obj = self.factory()
        with self.assertRaisesRegex(
            NotImplementedError, "Method only implemented for HpcUser objects"
        ):
            obj.get_user_email()

    def test_get_user_active(self):
        obj = self.factory()
        with self.assertRaisesRegex(
            NotImplementedError, "Method only implemented for HpcUser objects"
        ):
            obj.get_user_active()


class TestHpcProject(VersionTesterMixin, TestCase):
    """Tests for HpcProject model"""

    model = HpcProject
    version_model = HpcProjectVersion
    factory = HpcProjectFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        supplementaries = {
            "group": HpcGroupFactory(),
            "name": "hpc-project",
        }
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

    def test_generate_quota_report(self):
        obj = self.factory(
            resources_requested={
                "storage_green": 20,
                "storage_yellow": 20,
                "storage_red": 20,
                "storage_requested_only": 20,
            },
            resources_used={
                "storage_green": 10,
                "storage_yellow": 18,
                "storage_red": 20,
                "storage_used_only": 20,
            },
            folders={
                "storage_green": "/home/projects/green",
                "storage_yellow": "/home/projects/yellow",
                "storage_red": "/home/projects/red",
            },
        )
        expected = {
            "used": {
                "storage_green": 10,
                "storage_yellow": 18,
                "storage_red": 20,
            },
            "requested": {
                "storage_green": 20,
                "storage_yellow": 20,
                "storage_red": 20,
            },
            "percentage": {
                "storage_green": 50,
                "storage_yellow": 90,
                "storage_red": 100,
            },
            "status": {
                "storage_green": HpcQuotaStatus.GREEN,
                "storage_yellow": HpcQuotaStatus.YELLOW,
                "storage_red": HpcQuotaStatus.RED,
            },
            "folders": {
                "storage_green": "/home/projects/green",
                "storage_yellow": "/home/projects/yellow",
                "storage_red": "/home/projects/red",
            },
            "warnings": [
                "Resource storage_used_only is used, but not found in requested resources",
                "Resource storage_requested_only is requested, but not found in used resources",
            ],
        }
        self.assertDictEqual(obj.generate_quota_report(), expected)

    def test_get_manager_emails(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_emails(), {"delegate": "delegate@example.com"})

    def test_get_manager_emails_no_delegate(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup)
        self.assertEqual(obj.get_manager_emails(), {"owner": "owner@example.com"})

    def test_get_manager_emails_slim_false(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_emails(slim=False),
            {"owner": "owner@example.com", "delegate": "delegate@example.com"},
        )

    def test_get_manager_emails_invalid_address(self):
        user_owner = self.make_user("owner")
        user_owner.email = "INVALID"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup)
        self.assertEqual(obj.get_manager_emails(), {})

    def test_get_manager_names(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_names(), {"delegate": "Delegate"})

    def test_get_manager_names_no_delegate(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup)
        self.assertEqual(obj.get_manager_names(), {"owner": "Owner"})

    def test_get_manager_names_slim_false(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_names(slim=False), {"owner": "Owner", "delegate": "Delegate"}
        )

    def test_get_manager_contact(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_contact(),
            {"delegate": {"name": "Delegate", "email": "delegate@example.com"}},
        )

    def test_get_manager_contact_slim_false(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_contact(slim=False),
            {
                "owner": {"name": "Owner", "email": "owner@example.com"},
                "delegate": {"name": "Delegate", "email": "delegate@example.com"},
            },
        )

    def test_get_manager_contact_invalid_address(self):
        user_owner = self.make_user("owner")
        user_owner.last_name = "Owner"
        user_owner.save()
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        user_delegate.last_name = "Delegate"
        user_delegate.email = "INVALID"
        user_delegate.save()
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(
            obj.get_manager_contact(slim=False),
            {
                "owner": {"name": "Owner", "email": "owner@example.com"},
            },
        )

    def test_get_manager_active(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_active(), ["delegate"])

    def test_get_manager_active_no_delegate(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup)
        self.assertEqual(obj.get_manager_active(), ["owner"])

    def test_get_manager_active_slim_false(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate)
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_active(slim=False), ["delegate", "owner"])

    def test_get_manager_active_delegate_inactive(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner)
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate, status="EXPIRED")
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_active(), ["owner"])

    def test_get_manager_active_all_inactive(self):
        user_owner = self.make_user("owner")
        hpcuser_owner = HpcUserFactory(user=user_owner, status="EXPIRED")
        user_delegate = self.make_user("delegate")
        hpcuser_delegate = HpcUserFactory(user=user_delegate, status="EXPIRED")
        hpcgroup = HpcGroupFactory(owner=hpcuser_owner)
        obj = self.factory(group=hpcgroup, delegate=hpcuser_delegate)
        self.assertEqual(obj.get_manager_active(), [])

    def test_get_user_email(self):
        obj = self.factory()
        with self.assertRaisesRegex(
            NotImplementedError, "Method only implemented for HpcUser objects"
        ):
            obj.get_user_email()

    def test_get_user_active(self):
        obj = self.factory()
        with self.assertRaisesRegex(
            NotImplementedError, "Method only implemented for HpcUser objects"
        ):
            obj.get_user_active()


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

    def test_display_status(self):
        self._test_display_status()


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

    def test_display_status(self):
        self._test_display_status()


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

    def test_display_status(self):
        self._test_display_status()


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

    def test_display_status(self):
        self._test_display_status()


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

    def test_display_status(self):
        self._test_display_status()


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

    def test_display_status(self):
        self._test_display_status()


class TestHpcProjectChangeRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
    """Tests for HpcProjectChangeRequest model"""

    model = HpcProjectChangeRequest
    version_model = HpcProjectChangeRequestVersion
    factory = HpcProjectChangeRequestFactory

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

    def test_display_status(self):
        self._test_display_status()


class TestHpcProjectCreateRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
    """Tests for HpcProjectCreateRequest model"""

    model = HpcProjectCreateRequest
    version_model = HpcProjectCreateRequestVersion
    factory = HpcProjectCreateRequestFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        supplementaries = {
            "group": HpcGroupFactory(),
            "name_requested": "some-project",
        }
        self._test_save_with_version_new(**supplementaries)

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

    def test_display_status(self):
        self._test_display_status()


class TestHpcProjectDeleteRequest(RequestTesterMixin, VersionTesterMixin, TestCase):
    """Tests for HpcProjectDeleteRequest model"""

    model = HpcProjectDeleteRequest
    version_model = HpcProjectDeleteRequestVersion
    factory = HpcProjectDeleteRequestFactory

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

    def test_display_status(self):
        self._test_display_status()


class TestHpcGroupInvitation(VersionTesterMixin, TestCase):
    """Tests for HpcGroupInvitation model"""

    model = HpcGroupInvitation
    version_model = HpcGroupInvitationVersion
    factory = HpcGroupInvitationFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        supplementaries = {
            "hpcusercreaterequest": HpcUserCreateRequestFactory(),
            "username": "some-user",
        }
        self._test_save_with_version_new(**supplementaries)

    def test_save_with_version_existing(self):
        update = {"status": INVITATION_STATUS_ACCEPTED}
        self._test_save_with_version_existing(**update)

    def test_get_latest_version(self):
        update = {"status": INVITATION_STATUS_ACCEPTED}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()


class TestHpcProjectInvitation(VersionTesterMixin, TestCase):
    """Tests for HpcProjectInvitation model"""

    model = HpcProjectInvitation
    version_model = HpcProjectInvitationVersion
    factory = HpcProjectInvitationFactory

    def test_create_with_version(self):
        self._test_create_with_version()

    def test_create_with_version_two(self):
        self._test_create_with_version_two()

    def test_save_with_version_new(self):
        supplementaries = {
            "project": HpcProjectFactory(),
            "hpcprojectcreaterequest": HpcProjectCreateRequestFactory(),
            "user": HpcUserFactory(),
        }
        self._test_save_with_version_new(**supplementaries)

    def test_save_with_version_existing(self):
        update = {"status": INVITATION_STATUS_ACCEPTED}
        self._test_save_with_version_existing(**update)

    def test_get_latest_version(self):
        update = {"status": INVITATION_STATUS_ACCEPTED}
        self._test_get_latest_version(**update)

    def test_get_latest_version_not_available(self):
        self._test_get_latest_version_not_available()


class TestTermsAndConditions(TestCase):
    """Tests for TermsAndConditions model"""

    def test_create(self):
        tnc = TermsAndConditionsFactory()
        self.assertEqual(TermsAndConditions.objects.count(), 1)
        self.assertEqual(tnc.audience, TERMS_AUDIENCE_ALL)
        self.assertIsNone(tnc.date_published)
