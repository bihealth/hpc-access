from django.conf import settings
from django.urls import reverse
from django.utils import timezone
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
    REQUEST_STATUS_REVISION,
    TERMS_AUDIENCE_ALL,
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
    HpcProjectMembersEvent,
    HpcQuotaStatus,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
    HpcUserDeleteRequest,
    TermsAndConditions,
    get_next_hpcgroup_gid,
    get_next_hpcproject_gid,
    get_next_hpcuser_uid,
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
    hpc_event_obj_to_dict,
    hpc_obj_to_dict,
)


class RequestTesterMixin:
    """Mixin for testing methods of request objects."""

    model = None
    factory = None

    def _test_get_comment_history(self, comments):
        obj = self.factory(requester=self.user)
        history = [
            (
                self.user.username,
                obj.events.latest("pgh_id").pgh_created_at,
                obj.comment,
            )
        ]

        for comment in comments:
            obj.comment = comment
            obj.save()

            if comment:
                history.append(
                    (
                        self.user.username,
                        obj.events.latest("pgh_id").pgh_created_at,
                        comment,
                    )
                )

        self.assertEqual(history, obj.get_comment_history())

    def _test_get_comment_history_skips_repeated_comment(self):
        obj = self.factory(requester=self.user)
        initial = obj.comment
        obj.comment = "new comment"
        obj.save()
        obj.status = REQUEST_STATUS_ACTIVE  # leaves the comment as it is
        obj.save()

        self.assertEqual(
            [comment for _, _, comment in obj.get_comment_history()],
            [comment for comment in (initial, "new comment") if comment],
        )

    def _test_is_decided(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_DENIED)
        self.assertTrue(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_RETRACTED)
        self.assertFalse(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_APPROVED)
        self.assertTrue(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_ACTIVE)
        self.assertFalse(obj.is_decided())
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_REVISION)
        self.assertFalse(obj.is_decided())

    def _test_is_denied(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_DENIED)
        self.assertTrue(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_approved())
        self.assertFalse(obj.is_active())
        self.assertFalse(obj.is_revision())

    def _test_is_retracted(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_RETRACTED)
        self.assertTrue(obj.is_retracted())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_approved())
        self.assertFalse(obj.is_active())
        self.assertFalse(obj.is_revision())

    def _test_is_approved(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_APPROVED)
        self.assertTrue(obj.is_approved())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_active())
        self.assertFalse(obj.is_revision())

    def _test_is_active(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_ACTIVE)
        self.assertTrue(obj.is_active())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_approved())
        self.assertFalse(obj.is_revision())

    def _test_is_revision(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_REVISION)
        self.assertTrue(obj.is_revision())
        self.assertFalse(obj.is_denied())
        self.assertFalse(obj.is_retracted())
        self.assertFalse(obj.is_approved())
        self.assertFalse(obj.is_active())

    def _test_active(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_ACTIVE)
        self.factory(requester=self.user, status=REQUEST_STATUS_REVISION)
        self.factory(requester=self.user, status=REQUEST_STATUS_RETRACTED)
        self.factory(requester=self.user, status=REQUEST_STATUS_DENIED)
        self.factory(requester=self.user, status=REQUEST_STATUS_APPROVED)
        self.assertEqual(list(self.model.objects.active()), [obj])

    def _test_retracted(self):
        obj = self.factory(requester=self.user, status=REQUEST_STATUS_RETRACTED)
        self.factory(requester=self.user, status=REQUEST_STATUS_ACTIVE)
        self.factory(requester=self.user, status=REQUEST_STATUS_REVISION)
        self.factory(requester=self.user, status=REQUEST_STATUS_DENIED)
        self.factory(requester=self.user, status=REQUEST_STATUS_APPROVED)
        self.assertEqual(list(self.model.objects.retracted()), [obj])

    def _test_in_process(self):
        obj1 = self.factory(requester=self.user, status=REQUEST_STATUS_ACTIVE)
        obj2 = self.factory(requester=self.user, status=REQUEST_STATUS_REVISION)
        self.factory(requester=self.user, status=REQUEST_STATUS_RETRACTED)
        self.factory(requester=self.user, status=REQUEST_STATUS_DENIED)
        self.factory(requester=self.user, status=REQUEST_STATUS_APPROVED)
        self.assertEqual(list(self.model.objects.in_process()), [obj1, obj2])

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
            REQUEST_STATUS_APPROVED: "approved",
            REQUEST_STATUS_DENIED: "denied",
            REQUEST_STATUS_RETRACTED: "retracted",
        }

        for key, value in data.items():
            obj = self.factory(requester=self.user, status=key)
            self.assertEqual(obj.display_status(), value)

        obj = self.factory(requester=self.user, status="???")
        self.assertEqual(obj.display_status(), "unknown status")


class HistoryTesterMixin:
    """Mixin for testing the trigger-based history of a model."""

    model = None
    factory = None

    def setUp(self):
        super().setUp()

        self.maxDiff = None
        self.user = self.make_user("user")
        self.hpcadmin = self.make_user("hpcadmin")
        self.hpcadmin.is_hpcadmin = True
        self.hpcadmin.save()

    def _test_create_records_insert_event(self):
        obj = self.factory()
        obj.refresh_from_db()

        events = list(obj.events.order_by("pgh_id"))
        self.assertEqual([event.pgh_label for event in events], ["insert"])
        self.assertEqual(hpc_obj_to_dict(obj), hpc_event_obj_to_dict(events[0]))

    def _test_create_two_records_one_event_each(self):
        objs = [self.factory(), self.factory()]

        for obj in objs:
            obj.refresh_from_db()
            events = list(obj.events.all())
            self.assertEqual(len(events), 1)
            self.assertEqual(hpc_obj_to_dict(obj), hpc_event_obj_to_dict(events[0]))

    def __assert_update_event(self, obj, **update):
        obj.refresh_from_db()
        events = list(obj.events.order_by("pgh_id"))
        self.assertEqual([event.pgh_label for event in events], ["insert", "update"])

        before = hpc_event_obj_to_dict(events[0])
        after = hpc_event_obj_to_dict(events[1])
        self.assertEqual(after, hpc_obj_to_dict(obj))

        for field, value in update.items():
            self.assertEqual(after[field], value)
            self.assertNotEqual(before.pop(field), after.pop(field))

        self.assertEqual(before, after)

    def _test_save_existing(self, **update):
        obj = self.factory()

        for k, v in update.items():
            setattr(obj, k, v)

        obj.save()
        self.__assert_update_event(obj, **update)

    def _test_save_new(self, **supplementaries):
        obj = self.model()
        data = {k: v for k, v in vars(self.factory).items() if not k.startswith("_")}

        if supplementaries:
            data.update(supplementaries)

        for k, v in data.items():
            if not isinstance(v, SubFactory) and not isinstance(v, LazyAttribute):
                setattr(obj, k, v)

        obj.save()
        obj.refresh_from_db()

        self.assertEqual(self.model.objects.count(), 1)
        events = list(obj.events.all())
        self.assertEqual([event.pgh_label for event in events], ["insert"])
        self.assertEqual(hpc_obj_to_dict(obj), hpc_event_obj_to_dict(events[0]))

    def _test_queryset_update(self, **update):
        obj = self.factory()
        self.model.objects.filter(pk=obj.pk).update(**update)
        self.__assert_update_event(obj, **update)

    def _test_unchanged_save_records_no_event(self, **update):
        obj = self.factory()

        for k, v in update.items():
            setattr(obj, k, v)

        obj.save()
        obj.save()
        self.assertEqual(obj.events.count(), 2)

    def _test_timestamp_only_update_records_no_event(self):
        obj = self.factory()
        self.model.objects.filter(pk=obj.pk).update(date_modified=timezone.now())
        self.assertEqual(obj.events.count(), 1)

    def _test_ignored_field_update_records_no_event(self, **update):
        obj = self.factory()
        self.model.objects.filter(pk=obj.pk).update(**update)
        self.assertEqual(obj.events.count(), 1)

    def _test_soft_delete(self):
        obj = self.factory()
        self.assertEqual(obj.status, OBJECT_STATUS_INITIAL)
        obj.soft_delete()
        self.__assert_update_event(obj, status=OBJECT_STATUS_DELETED)

    def _test_retract(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.retract()
        self.__assert_update_event(obj, status=REQUEST_STATUS_RETRACTED)

    def _test_deny(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.deny()
        self.__assert_update_event(obj, status=REQUEST_STATUS_DENIED)

    def _test_approve(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.approve()
        self.__assert_update_event(obj, status=REQUEST_STATUS_APPROVED)

    def _test_request_revision(self):
        obj = self.factory()
        self.assertEqual(obj.status, REQUEST_STATUS_INITIAL)
        obj.request_revision()
        self.__assert_update_event(obj, status=REQUEST_STATUS_REVISION)

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


class PendingRequestTesterMixin:
    change_request_factory = None
    delete_request_factory = None
    obj_type = None

    def _test_has_pending_delete_request(self):
        obj = self.factory()
        data = {self.obj_type: obj}
        request = self.delete_request_factory(**data)

        for status in (REQUEST_STATUS_ACTIVE, REQUEST_STATUS_REVISION):
            request.status = status
            request.save()
            self.assertTrue(obj.has_pending_delete_request())

        for status in (REQUEST_STATUS_APPROVED, REQUEST_STATUS_DENIED, REQUEST_STATUS_RETRACTED):
            request.status = status
            request.save()
            self.assertFalse(obj.has_pending_delete_request())

    def _test_has_pending_change_request(self):
        obj = self.factory()
        data = {self.obj_type: obj}
        request = self.change_request_factory(**data)

        for status in (REQUEST_STATUS_ACTIVE, REQUEST_STATUS_REVISION):
            request.status = status
            request.save()
            self.assertTrue(obj.has_pending_change_request())

        for status in (REQUEST_STATUS_APPROVED, REQUEST_STATUS_DENIED, REQUEST_STATUS_RETRACTED):
            request.status = status
            request.save()
            self.assertFalse(obj.has_pending_change_request())

    def _test_has_retracted_change_request(self):
        obj = self.factory()
        request = self.change_request_factory(
            **{self.obj_type: obj, "status": REQUEST_STATUS_RETRACTED}
        )
        self.assertTrue(obj.has_retracted_change_request())

        for status in (
            REQUEST_STATUS_ACTIVE,
            REQUEST_STATUS_REVISION,
            REQUEST_STATUS_APPROVED,
            REQUEST_STATUS_DENIED,
        ):
            request.status = status
            request.save()
            self.assertFalse(obj.has_retracted_change_request())

    def _test_has_retracted_delete_request(self):
        obj = self.factory()
        request = self.delete_request_factory(
            **{self.obj_type: obj, "status": REQUEST_STATUS_RETRACTED}
        )
        self.assertTrue(obj.has_retracted_delete_request())

        for status in (
            REQUEST_STATUS_ACTIVE,
            REQUEST_STATUS_REVISION,
            REQUEST_STATUS_APPROVED,
            REQUEST_STATUS_DENIED,
        ):
            request.status = status
            request.save()
            self.assertFalse(obj.has_retracted_delete_request())

    def _test_retracted_delete_request(self):
        obj = self.factory()
        request = self.delete_request_factory(
            **{self.obj_type: obj, "status": REQUEST_STATUS_RETRACTED}
        )
        self.assertEqual(obj.retracted_delete_request(), request)

    def _test_retracted_change_request(self):
        obj = self.factory()
        request = self.change_request_factory(
            **{self.obj_type: obj, "status": REQUEST_STATUS_RETRACTED}
        )
        self.assertEqual(obj.retracted_change_request(), request)

    def _test_has_pending_requests(self):
        obj = self.factory()
        self.change_request_factory(**{self.obj_type: obj, "status": REQUEST_STATUS_ACTIVE})
        self.delete_request_factory(**{self.obj_type: obj, "status": REQUEST_STATUS_RETRACTED})
        self.assertTrue(obj.has_pending_requests())

    def _test_has_pending_requests_false(self):
        obj = self.factory()
        self.change_request_factory(**{self.obj_type: obj, "status": REQUEST_STATUS_RETRACTED})
        self.delete_request_factory(**{self.obj_type: obj, "status": REQUEST_STATUS_RETRACTED})
        self.assertFalse(obj.has_pending_requests())


class TestGetNextIdFunctions(TestCase):
    def test_get_next_hpcuser_id(self):
        HpcUserFactory(uid=2000)
        HpcUserFactory(uid=2002)
        self.assertEqual(get_next_hpcuser_uid(), 2003)

    def test_get_next_hpcuser_id_all_none(self):
        HpcUserFactory(uid=None)
        self.assertEqual(get_next_hpcuser_uid(), 1)

    def test_get_next_hpcgroup_id(self):
        HpcGroupFactory(gid=5000)
        HpcGroupFactory(gid=5002)
        self.assertEqual(get_next_hpcgroup_gid(), 5003)

    def test_get_next_hpcgroup_id_all_none(self):
        HpcGroupFactory(gid=None)
        self.assertEqual(get_next_hpcgroup_gid(), 1)

    def test_get_next_hpcproject_id(self):
        HpcProjectFactory(gid=6000)
        HpcProjectFactory(gid=6002)
        self.assertEqual(get_next_hpcproject_gid(), 6003)

    def test_get_next_hpcproject_id_all_none(self):
        HpcProjectFactory(gid=None)
        self.assertEqual(get_next_hpcproject_gid(), 1)


class TestHpcUser(HistoryTesterMixin, PendingRequestTesterMixin, TestCase):
    """Tests for HpcUser model"""

    # History Tester Mixin
    model = HpcUser
    factory = HpcUserFactory

    # Pending Request Tester Mixin
    obj_type = "user"
    change_request_factory = HpcUserChangeRequestFactory
    delete_request_factory = HpcUserDeleteRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        supplementaries = {
            "primary_group": HpcGroupFactory(),
            "username": "user_" + settings.INSTITUTE_USERNAME_SUFFIX,
        }
        self._test_save_new(**supplementaries)

    def test_save_existing(self):
        update = {"description": "description updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"description": "description updated"}
        self._test_queryset_update(**update)

    def test_soft_delete(self):
        self._test_soft_delete()

    def test_unchanged_save_records_no_event(self):
        update = {"description": "description updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

    def test_resources_used_only_update_records_no_event(self):
        self._test_ignored_field_update_records_no_event(resources_used={"tier1_home": 99})

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

    def test_is_pi_false(self):
        user = self.factory()
        self.assertFalse(user.is_pi)

    def test_is_pi_true(self):
        user = self.factory(primary_group=None)
        user.primary_group = HpcGroupFactory(owner=user)
        user.save()
        self.assertTrue(user.is_pi)

    def test_role_pi(self):
        user = self.factory(primary_group=None)
        user.primary_group = HpcGroupFactory(owner=user)
        user.save()
        self.assertEqual(user.role, "PI")

    def test_role_delegate(self):
        user = self.factory(primary_group=None)
        user.primary_group = HpcGroupFactory(delegate=user)
        user.save()
        self.assertEqual(user.role, "Delegate")

    def test_role_member(self):
        user = self.factory()
        self.assertEqual(user.role, "Member")

    def test_role_alumni(self):
        user = self.factory(primary_group=None)
        self.assertEqual(user.role, "Alumni")

    def test_has_pending_delete_request(self):
        self._test_has_pending_delete_request()

    def test_has_pending_change_request(self):
        self._test_has_pending_change_request()

    def test_has_retracted_change_request(self):
        self._test_has_retracted_change_request()

    def test_has_retracted_delete_request(self):
        self._test_has_retracted_delete_request()

    def test_retracted_delete_request(self):
        self._test_retracted_delete_request()

    def test_retracted_change_request(self):
        self._test_retracted_change_request()

    def test_has_pending_requests(self):
        self._test_has_pending_requests()

    def test_has_pending_requests_false(self):
        self._test_has_pending_requests_false()

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

    def test_generate_quota_report_zero_quota(self):
        user = self.factory(
            resources_requested={TIER_USER_HOME: 0},
            resources_used={TIER_USER_HOME: 0},
            home_directory="/home/users",
        )
        expected = {
            "used": {TIER_USER_HOME: 0},
            "requested": {TIER_USER_HOME: 0},
            "percentage": {TIER_USER_HOME: 0},
            "status": {TIER_USER_HOME: HpcQuotaStatus.GREEN},
            "folders": {TIER_USER_HOME: "/home/users"},
            "warnings": [],
        }

        self.assertDictEqual(user.generate_quota_report(), expected)

    def test_generate_quota_report_no_resources(self):
        user = self.factory(
            resources_requested={},
            resources_used={},
            home_directory="/home/users",
        )
        expected = {
            "used": {},
            "requested": {},
            "percentage": {},
            "status": {},
            "folders": {},
            "warnings": ["No resources available."],
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


class TestHpcGroup(HistoryTesterMixin, PendingRequestTesterMixin, TestCase):
    """Tests for HpcGroup model"""

    model = HpcGroup
    factory = HpcGroupFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        supplementaries = {"name": "hpc-group"}
        self._test_save_new(**supplementaries)

    def test_save_existing(self):
        update = {"description": "description updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"description": "description updated"}
        self._test_queryset_update(**update)

    def test_soft_delete(self):
        self._test_soft_delete()

    def test_unchanged_save_records_no_event(self):
        update = {"description": "description updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

    def test_resources_used_only_update_records_no_event(self):
        self._test_ignored_field_update_records_no_event(resources_used={"tier1_work": 99})

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

    # def test_has_pending_delete_request(self):
    #     self._test_has_pending_delete_request()

    # def test_has_pending_change_request(self):
    #     self._test_has_pending_change_request()

    # def test_has_retracted_change_request(self):
    #     self._test_has_retracted_change_request()

    # def test_has_retracted_delete_request(self):
    #     self._test_has_retracted_delete_request()

    # def test_retracted_delete_request(self):
    #     self._test_retracted_delete_request()

    # def test_retracted_change_request(self):
    #     self._test_retracted_change_request()

    # def test_has_pending_requests(self):
    #     self._test_has_pending_requests()

    # def test_has_pending_requests_false(self):
    #     self._test_has_pending_requests_false()


class TestHpcProject(HistoryTesterMixin, PendingRequestTesterMixin, TestCase):
    """Tests for HpcProject model"""

    model = HpcProject
    factory = HpcProjectFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        supplementaries = {
            "group": HpcGroupFactory(),
            "name": "hpc-project",
        }
        self._test_save_new(**supplementaries)

    def test_save_existing(self):
        update = {"description": "description updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"description": "description updated"}
        self._test_queryset_update(**update)

    def test_soft_delete(self):
        self._test_soft_delete()

    def test_unchanged_save_records_no_event(self):
        update = {"description": "description updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

    def test_resources_used_only_update_records_no_event(self):
        self._test_ignored_field_update_records_no_event(resources_used={"tier1_work": 99})

    def test_members_history(self):
        project = self.factory()
        user1, user2 = HpcUserFactory(), HpcUserFactory()
        project.members.add(user1)
        project.members.add(user2)
        project.members.remove(user1)

        self.assertEqual(
            [
                (event.pgh_label, event.hpcuser)
                for event in HpcProjectMembersEvent.objects.filter(
                    hpcproject=project, hpcuser__in=[user1, user2]
                ).order_by("pgh_id")
            ],
            [("members.add", user1), ("members.add", user2), ("members.remove", user1)],
        )

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

    # def test_has_pending_delete_request(self):
    #     self._test_has_pending_delete_request()

    # def test_has_pending_change_request(self):
    #     self._test_has_pending_change_request()

    # def test_has_retracted_change_request(self):
    #     self._test_has_retracted_change_request()

    # def test_has_retracted_delete_request(self):
    #     self._test_has_retracted_delete_request()

    # def test_retracted_delete_request(self):
    #     self._test_retracted_delete_request()

    # def test_retracted_change_request(self):
    #     self._test_retracted_change_request()

    # def test_has_pending_requests(self):
    #     self._test_has_pending_requests()

    # def test_has_pending_requests_false(self):
    #     self._test_has_pending_requests_false()


class TestHpcGroupChangeRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcGroupChangeRequest model"""

    model = HpcGroupChangeRequest
    factory = HpcGroupChangeRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        self._test_save_new()

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcGroupCreateRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcGroupCreateRequest model"""

    model = HpcGroupCreateRequest
    factory = HpcGroupCreateRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        self._test_save_new()

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

    def test_get_detail_url_user(self):
        self._test_get_detail_url_user()

    def test_get_detail_url_admin(self):
        self._test_get_detail_url_admin()

    def test_get_comment_history(self):
        comments = ["new comment", "", "even more comments"]
        self._test_get_comment_history(comments)

    def test_get_comment_history_skips_repeated_comment(self):
        self._test_get_comment_history_skips_repeated_comment()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcGroupDeleteRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcGroupDeleteRequest model"""

    model = HpcGroupDeleteRequest
    factory = HpcGroupDeleteRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        self._test_save_new()

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcUserChangeRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcUserChangeRequest model"""

    model = HpcUserChangeRequest
    factory = HpcUserChangeRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        self._test_save_new()

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcUserCreateRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcUserCreateRequest model"""

    model = HpcUserCreateRequest
    factory = HpcUserCreateRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        self._test_save_new()

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcUserDeleteRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcUserDeleteRequest model"""

    model = HpcUserDeleteRequest
    factory = HpcUserDeleteRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        self._test_save_new()

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcProjectChangeRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcProjectChangeRequest model"""

    model = HpcProjectChangeRequest
    factory = HpcProjectChangeRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        self._test_save_new()

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcProjectCreateRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcProjectCreateRequest model"""

    model = HpcProjectCreateRequest
    factory = HpcProjectCreateRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        supplementaries = {
            "group": HpcGroupFactory(),
            "name_requested": "some-project",
        }
        self._test_save_new(**supplementaries)

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcProjectDeleteRequest(RequestTesterMixin, HistoryTesterMixin, TestCase):
    """Tests for HpcProjectDeleteRequest model"""

    model = HpcProjectDeleteRequest
    factory = HpcProjectDeleteRequestFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        self._test_save_new()

    def test_save_existing(self):
        update = {"comment": "comment updated"}
        self._test_save_existing(**update)

    def test_queryset_update(self):
        update = {"comment": "comment updated"}
        self._test_queryset_update(**update)

    def test_retract(self):
        self._test_retract()

    def test_deny(self):
        self._test_deny()

    def test_approve(self):
        self._test_approve()

    def test_request_revision(self):
        self._test_request_revision()

    def test_unchanged_save_records_no_event(self):
        update = {"comment": "comment updated"}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()

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

    def test_is_revision(self):
        self._test_is_revision()

    def test_active(self):
        self._test_active()

    def test_in_process(self):
        self._test_in_process()

    def test_retracted(self):
        self._test_retracted()

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


class TestHpcGroupInvitation(HistoryTesterMixin, TestCase):
    """Tests for HpcGroupInvitation model"""

    model = HpcGroupInvitation
    factory = HpcGroupInvitationFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        supplementaries = {
            "hpcusercreaterequest": HpcUserCreateRequestFactory(),
            "username": "some-user",
        }
        self._test_save_new(**supplementaries)

    def test_save_existing(self):
        update = {"status": INVITATION_STATUS_ACCEPTED}
        self._test_save_existing(**update)

    def test_unchanged_save_records_no_event(self):
        update = {"status": INVITATION_STATUS_ACCEPTED}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()


class TestHpcProjectInvitation(HistoryTesterMixin, TestCase):
    """Tests for HpcProjectInvitation model"""

    model = HpcProjectInvitation
    factory = HpcProjectInvitationFactory

    def test_create_records_insert_event(self):
        self._test_create_records_insert_event()

    def test_create_two_records_one_event_each(self):
        self._test_create_two_records_one_event_each()

    def test_save_new(self):
        supplementaries = {
            "project": HpcProjectFactory(),
            "hpcprojectcreaterequest": HpcProjectCreateRequestFactory(),
            "user": HpcUserFactory(),
        }
        self._test_save_new(**supplementaries)

    def test_save_existing(self):
        update = {"status": INVITATION_STATUS_ACCEPTED}
        self._test_save_existing(**update)

    def test_unchanged_save_records_no_event(self):
        update = {"status": INVITATION_STATUS_ACCEPTED}
        self._test_unchanged_save_records_no_event(**update)

    def test_timestamp_only_update_records_no_event(self):
        self._test_timestamp_only_update_records_no_event()


class TestTermsAndConditions(TestCase):
    """Tests for TermsAndConditions model"""

    def test_create(self):
        tnc = TermsAndConditionsFactory()
        self.assertEqual(TermsAndConditions.objects.count(), 1)
        self.assertEqual(tnc.audience, TERMS_AUDIENCE_ALL)
        self.assertIsNone(tnc.date_published)
