from django.urls import reverse
from django.utils import timezone
from django.utils.datetime_safe import datetime
from test_plus.test import TestCase

from usersec.forms import (
    HpcGroupCreateRequestForm,
    HpcUserCreateRequestForm,
    HpcProjectCreateRequestForm,
    HpcGroupChangeRequestForm,
    HpcUserChangeRequestForm,
    UserSelectForm,
)
from usersec.tests.factories import (
    HPCGROUPCREATEREQUEST_FORM_DATA_VALID,
    HPCUSERCREATEREQUEST_FORM_DATA_VALID,
    HPCPROJECTCREATEREQUEST_FORM_DATA_VALID,
    HpcUserFactory,
    HpcGroupFactory,
    HPCGROUPCHANGEREQUEST_FORM_DATA_VALID,
    HPCUSERCHANGEREQUEST_FORM_DATA_VALID,
)


class TestHpcGroupCreateRequestForm(TestCase):
    """Tests for HpcGroupCreateRequest form."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("user")
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()
        self.data_valid = HPCGROUPCREATEREQUEST_FORM_DATA_VALID

    def test_form_valid(self):
        form = HpcGroupCreateRequestForm(user=self.user, data=self.data_valid)
        self.assertTrue(form.is_valid())
        expiration_expected = datetime(year=timezone.now().year + 1, month=1, day=31)
        self.assertEqual(form.cleaned_data["expiration"].year, expiration_expected.year)
        self.assertEqual(form.cleaned_data["expiration"].month, expiration_expected.month)
        self.assertEqual(form.cleaned_data["expiration"].day, expiration_expected.day)

    def test_form_invalid_resources_requested_missing(self):
        data_invalid = {**self.data_valid, "resources_requested": {}}
        form = HpcGroupCreateRequestForm(user=self.user, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["resources_requested"], ["This field is required."])

    def test_form_valid_hpcadmin(self):
        form = HpcGroupCreateRequestForm(user=self.user_hpcadmin, data=self.data_valid)
        self.assertTrue(form.is_valid())

    def test_form_invalid_hpcadmin_comment_missing(self):
        data_invalid = {**self.data_valid, "comment": ""}
        form = HpcGroupCreateRequestForm(user=self.user_hpcadmin, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["comment"], ["This field is required."])


class TestHpcGroupChangeRequestForm(TestCase):
    """Tests for HpcGroupChangeRequest form."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("user")
        self.user_owner = self.make_user("owner")
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()

        self.hpc_group = HpcGroupFactory()
        self.hpc_owner = HpcUserFactory(user=self.user_owner, primary_group=self.hpc_group)
        self.hpc_group.owner = self.hpc_owner
        self.hpc_group.save()

        self.data_valid = HPCGROUPCHANGEREQUEST_FORM_DATA_VALID

    def test_form_initials(self):
        form = HpcGroupChangeRequestForm(user=self.user_owner, group=self.hpc_group)
        self.assertEqual(form.fields["description"].initial, self.hpc_group.description)
        expiration_expected = datetime(year=timezone.now().year + 1, month=1, day=31)
        self.assertEqual(form.fields["expiration"].initial, expiration_expected)
        self.assertEqual(form.fields["delegate"].initial, self.hpc_group.delegate)
        self.assertEqual(
            form.fields["resources_requested"].initial, self.hpc_group.resources_requested
        )
        self.assertEqual(
            form.fields["tier1"].initial, self.hpc_group.resources_requested.get("tier1")
        )
        self.assertEqual(
            form.fields["tier2"].initial, self.hpc_group.resources_requested.get("tier2")
        )

    def test_form_valid(self):
        form = HpcGroupChangeRequestForm(
            user=self.user_owner, group=self.hpc_group, data=self.data_valid
        )
        self.assertTrue(form.is_valid())

    def test_form_invalid_expiration_missing(self):
        data_invalid = dict(self.data_valid)
        data_invalid["expiration"] = ""
        form = HpcGroupChangeRequestForm(
            user=self.user_owner, group=self.hpc_group, data=data_invalid
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["expiration"], ["This field is required."])

    def test_form_invalid_resources_requested_missing(self):
        data_invalid = {**self.data_valid, "resources_requested": {}}
        form = HpcGroupChangeRequestForm(
            user=self.user_owner, group=self.hpc_group, data=data_invalid
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["resources_requested"], ["This field is required."])

    def test_form_valid_hpcadmin(self):
        form = HpcGroupChangeRequestForm(
            user=self.user_hpcadmin, group=self.hpc_group, data=self.data_valid
        )
        self.assertTrue(form.is_valid())

    def test_form_invalid_hpcadmin_comment_missing(self):
        data_invalid = {**self.data_valid, "comment": ""}
        form = HpcGroupChangeRequestForm(
            user=self.user_hpcadmin, group=self.hpc_group, data=data_invalid
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["comment"], ["This field is required."])


class TestHpcUserCreateRequestForm(TestCase):
    """Tests for HpcUserCreateRequest form."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("user")
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()
        self.data_valid = HPCUSERCREATEREQUEST_FORM_DATA_VALID

    def test_form_valid(self):
        form = HpcUserCreateRequestForm(user=self.user, data=self.data_valid)
        self.assertTrue(form.is_valid())
        expiration_expected = datetime(year=timezone.now().year + 1, month=1, day=31)
        self.assertEqual(form.cleaned_data["expiration"].year, expiration_expected.year)
        self.assertEqual(form.cleaned_data["expiration"].month, expiration_expected.month)
        self.assertEqual(form.cleaned_data["expiration"].day, expiration_expected.day)

    def test_form_invalid_resources_requested_missing(self):
        data_invalid = {**self.data_valid, "resources_requested": {}}
        form = HpcUserCreateRequestForm(user=self.user, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["resources_requested"], ["This field is required."])

    def test_form_invalid_email_missing(self):
        data_invalid = {**self.data_valid, "email": ""}
        form = HpcUserCreateRequestForm(user=self.user, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["email"], ["This field is required."])

    def test_form_invalid_email_wrong_domain(self):
        data_invalid = {**self.data_valid, "email": "user@invalid.com"}
        form = HpcUserCreateRequestForm(user=self.user, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["email"], ["No institute email address."])

    def test_form_valid_hpcadmin(self):
        form = HpcUserCreateRequestForm(user=self.user_hpcadmin, data=self.data_valid)
        self.assertTrue(form.is_valid())

    def test_form_invalid_hpcadmin_comment_missing(self):
        data_invalid = {**self.data_valid, "comment": ""}
        form = HpcUserCreateRequestForm(user=self.user_hpcadmin, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["comment"], ["This field is required."])


class TestHpcUserChangeRequestForm(TestCase):
    """Tests for HpcUserChangeRequest form."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("user")
        self.user_owner = self.make_user("owner")
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()

        self.data_valid = HPCUSERCHANGEREQUEST_FORM_DATA_VALID

    def test_form_initials(self):
        form = HpcUserChangeRequestForm(user=self.user_owner)
        expiration_expected = datetime(year=timezone.now().year + 1, month=1, day=31)
        self.assertEqual(form.fields["expiration"].initial, expiration_expected)

    def test_form_valid(self):
        form = HpcUserChangeRequestForm(user=self.user_owner, data=self.data_valid)
        self.assertTrue(form.is_valid())

    def test_form_invalid_expiration_missing(self):
        data_invalid = dict(self.data_valid)
        data_invalid["expiration"] = ""
        form = HpcUserChangeRequestForm(user=self.user_owner, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["expiration"], ["This field is required."])

    def test_form_valid_hpcadmin(self):
        form = HpcUserChangeRequestForm(user=self.user_hpcadmin, data=self.data_valid)
        self.assertTrue(form.is_valid())

    def test_form_invalid_hpcadmin_comment_missing(self):
        data_invalid = {**self.data_valid, "comment": ""}
        form = HpcUserChangeRequestForm(user=self.user_hpcadmin, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["comment"], ["This field is required."])


class TestHpcProjectCreateRequestForm(TestCase):
    """Tests for HpcProjectCreateRequest form."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("user")
        user_owner = self.make_user("owner")
        self.user_hpcadmin = self.make_user("hpcadmin")
        self.user_hpcadmin.is_hpcadmin = True
        self.user_hpcadmin.save()

        self.hpc_group = HpcGroupFactory()
        self.hpc_owner = HpcUserFactory(user=user_owner, primary_group=self.hpc_group)
        self.hpc_group.owner = self.hpc_owner
        self.hpc_group.save()

        self.data_valid = HPCPROJECTCREATEREQUEST_FORM_DATA_VALID
        self.data_valid["members"] = [HpcUserFactory(user=self.user)]

    def test_form_valid(self):
        form = HpcProjectCreateRequestForm(
            user=self.user, group=self.hpc_group, data=self.data_valid
        )
        self.assertTrue(form.is_valid())
        expiration_expected = datetime(year=timezone.now().year + 1, month=1, day=31)
        self.assertEqual(form.cleaned_data["expiration"].year, expiration_expected.year)
        self.assertEqual(form.cleaned_data["expiration"].month, expiration_expected.month)
        self.assertEqual(form.cleaned_data["expiration"].day, expiration_expected.day)

    def test_form_invalid_resources_requested_missing(self):
        data_invalid = {**self.data_valid, "resources_requested": {}}
        form = HpcProjectCreateRequestForm(user=self.user, group=self.hpc_group, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["resources_requested"], ["This field is required."])

    def test_form_invalid_name_missing(self):
        data_invalid = {**self.data_valid, "name": ""}
        form = HpcProjectCreateRequestForm(user=self.user, group=self.hpc_group, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["name"], ["This field is required."])

    def test_form_invalid_members_missing(self):
        data_invalid = {**self.data_valid, "members": None}
        form = HpcProjectCreateRequestForm(user=self.user, group=self.hpc_group, data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["members"], ["This field is required."])

    def test_form_valid_hpcadmin(self):
        form = HpcProjectCreateRequestForm(
            user=self.user_hpcadmin, group=self.hpc_group, data=self.data_valid
        )
        self.assertTrue(form.is_valid())

    def test_form_invalid_hpcadmin_comment_missing(self):
        data_invalid = {**self.data_valid, "comment": ""}
        form = HpcProjectCreateRequestForm(
            user=self.user_hpcadmin, group=self.hpc_group, data=data_invalid
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["comment"], ["This field is required."])


class TestUserSelectForm(TestCase):
    """Tests for UserSelect form."""

    def setUp(self):
        super().setUp()
        user_owner = self.make_user("owner")

        self.hpc_group = HpcGroupFactory()
        self.hpc_owner = HpcUserFactory(user=user_owner, primary_group=self.hpc_group)
        self.hpc_group.owner = self.hpc_owner
        self.hpc_group.save()

    def test_form(self):
        form = UserSelectForm(group=self.hpc_group)

        self.assertEqual(
            form.fields["members"].choices,
            [
                (
                    reverse(
                        "usersec:hpcuserchangerequest-create",
                        kwargs={"hpcuser": self.hpc_owner.uuid},
                    ),
                    str(self.hpc_owner),
                )
            ],
        )
