from django.test import TestCase

from usersec.forms import HpcGroupCreateRequestForm
from usersec.tests.factories import HPCGROUPCREATEREQUESTFORM_DATA_VALID


class TestHpcGroupCreateRequestForm(TestCase):
    def setUp(self):
        super().setUp()
        self.data_valid = HPCGROUPCREATEREQUESTFORM_DATA_VALID

    def test_form_valid(self):
        form = HpcGroupCreateRequestForm(self.data_valid)
        self.assertTrue(form.is_valid())

    def test_form_invalid_resources_requested_missing(self):
        data_invalid = {**self.data_valid, "resources_requested": {}}
        form = HpcGroupCreateRequestForm(data_invalid)
        self.assertEqual(
            form.errors["resources_requested"], ["This field is required."]
        )

    def test_form_invalid_expiration_missing(self):
        data_invalid = {**self.data_valid, "expiration": ""}
        form = HpcGroupCreateRequestForm(data_invalid)
        self.assertEqual(form.errors["expiration"], ["This field is required."])

    def test_form_invalid_description_missing(self):
        data_invalid = {**self.data_valid, "description": {}}
        form = HpcGroupCreateRequestForm(data_invalid)
        self.assertEqual(
            form.errors["description"], ["This field is required."]
        )
