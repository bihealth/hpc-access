from test_plus.test import TestCase

from usersec.forms import HpcGroupCreateRequestForm, HpcUserCreateRequestForm
from usersec.tests.factories import (
    HPCGROUPCREATEREQUESTFORM_DATA_VALID,
    HPCUSERCREATEREQUESTFORM_DATA_VALID,
)


class TestHpcGroupCreateRequestForm(TestCase):
    """Tests for HpcGroupCreateRequest form."""

    def setUp(self):
        super().setUp()
        self.data_valid = HPCGROUPCREATEREQUESTFORM_DATA_VALID

    def test_form_valid(self):
        form = HpcGroupCreateRequestForm(data=self.data_valid)
        self.assertTrue(form.is_valid())

    def test_form_invalid_resources_requested_missing(self):
        data_invalid = {**self.data_valid, "resources_requested": {}}
        form = HpcGroupCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["resources_requested"], ["This field is required."])

    def test_form_invalid_resources_requested_not_dict(self):
        data_invalid = {
            **self.data_valid,
            "resources_requested": ["I'm", "a", "list"],
        }
        form = HpcGroupCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["resources_requested"],
            ["Resources must be a dictionary!"],
        )

    def test_form_invalid_expiration_missing(self):
        data_invalid = {**self.data_valid, "expiration": ""}
        form = HpcGroupCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["expiration"], ["This field is required."])

    def test_form_invalid_description_missing(self):
        data_invalid = {**self.data_valid, "description": ""}
        form = HpcGroupCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["description"], ["This field is required."])

    def test_form_invalid_comment_missing(self):
        data_invalid = {**self.data_valid, "comment": ""}
        form = HpcGroupCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["comment"], ["This field is required."])

    def test_form_valid_hpcadmin(self):
        user_hpcadmin = self.make_user("hpcadmin")
        user_hpcadmin.is_hpcadmin = True
        user_hpcadmin.save()
        form = HpcGroupCreateRequestForm(user=user_hpcadmin, data=self.data_valid)
        self.assertTrue(form.is_valid())

    # TODO remove
    # def test_form_invalid_hpcadmin_comment_missing(self):
    #     user_hpcadmin = self.make_user("hpcadmin")
    #     user_hpcadmin.is_hpcadmin = True
    #     user_hpcadmin.save()
    #     data_invalid = {**self.data_valid, "comment": ""}
    #     form = HpcGroupCreateRequestForm(user=user_hpcadmin, data=data_invalid)
    #     self.assertFalse(form.is_valid())
    #     self.assertEqual(form.errors["comment"], ["This field is required."])


class TestHpcUserCreateRequestForm(TestCase):
    """Tests for HpcUserCreateRequest form."""

    def setUp(self):
        super().setUp()
        self.data_valid = HPCUSERCREATEREQUESTFORM_DATA_VALID

    def test_form_valid(self):
        form = HpcUserCreateRequestForm(data=self.data_valid)
        self.assertTrue(form.is_valid())

    def test_form_invalid_resources_requested_missing(self):
        data_invalid = {**self.data_valid, "resources_requested": {}}
        form = HpcUserCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["resources_requested"], ["This field is required."])

    def test_form_invalid_resources_requested_not_dict(self):
        data_invalid = {
            **self.data_valid,
            "resources_requested": ["I'm", "a", "list"],
        }
        form = HpcUserCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["resources_requested"],
            ["Resources must be a dictionary!"],
        )

    def test_form_invalid_expiration_missing(self):
        data_invalid = {**self.data_valid, "expiration": ""}
        form = HpcUserCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["expiration"], ["This field is required."])

    def test_form_invalid_email_missing(self):
        data_invalid = {**self.data_valid, "email": ""}
        form = HpcUserCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["email"], ["This field is required."])

    def test_form_invalid_email_wrong_domain(self):
        data_invalid = {**self.data_valid, "email": "user@example.com"}
        form = HpcUserCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["email"], ["No institute email address."])

    def test_form_invalid_comment_missing(self):
        data_invalid = {**self.data_valid, "comment": ""}
        form = HpcUserCreateRequestForm(data=data_invalid)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["comment"], ["This field is required."])

    def test_form_valid_hpcadmin(self):
        user_hpcadmin = self.make_user("hpcadmin")
        user_hpcadmin.is_hpcadmin = True
        user_hpcadmin.save()
        form = HpcUserCreateRequestForm(user=user_hpcadmin, data=self.data_valid)
        self.assertTrue(form.is_valid())
