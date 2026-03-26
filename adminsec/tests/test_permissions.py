from django.urls import reverse

from usersec.models import (
    TERMS_AUDIENCE_PI,
    TERMS_AUDIENCE_USER,
    TermsAndConditions,
)
from usersec.tests.factories import (
    TermsAndConditionsFactory,
)
from usersec.tests.test_views import TestViewBase


class TestTermsAndConditionsListViewPermissions(TestViewBase):
    """Tests for TermsAndConditionsListView."""

    def setUp(self):
        super().setUp()
        self.terms_all = TermsAndConditionsFactory()
        self.terms_pi = TermsAndConditionsFactory(title="For PIs", audience=TERMS_AUDIENCE_PI)
        self.terms_users = TermsAndConditionsFactory(
            title="For Users", audience=TERMS_AUDIENCE_USER
        )

    def test_get_allowed(self):
        for user in [self.user_hpcadmin, self.superuser]:
            with self.login(user):
                response = self.client.get(reverse("adminsec:termsandconditions-list"))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context["object_list"]), 3)
                self.assertListEqual(
                    list(response.context["object_list"]),
                    [self.terms_all, self.terms_pi, self.terms_users],
                )
                self.assertTrue(response.context["not_published"])

    def test_get_denied(self):
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.get(reverse("adminsec:termsandconditions-list"))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))


class TestTermsAndConditionsCreateViewPermissions(TestViewBase):
    """Tests for TermsAndConditionsCreateView."""

    def setUp(self):
        super().setUp()
        self.terms = {
            "title": "Terms and Conditions",
            "text": "Content",
            "audience": TERMS_AUDIENCE_USER,
        }

    def test_get_allowed(self):
        for user in [self.user_hpcadmin, self.superuser]:
            with self.login(user):
                response = self.client.get(reverse("adminsec:termsandconditions-create"))
                self.assertEqual(response.status_code, 200)
                self.assertIsNotNone(response.context["form"])

    def test_post_allowed(self):
        for user in [self.user_hpcadmin, self.superuser]:
            with self.login(user):
                self.assertEqual(TermsAndConditions.objects.count(), 0)
                response = self.client.post(
                    reverse("adminsec:termsandconditions-create"),
                    self.terms,
                )
                self.assertRedirects(
                    response,
                    reverse("adminsec:termsandconditions-list"),
                )
                self.assertEqual(TermsAndConditions.objects.count(), 1)
                TermsAndConditions.objects.first().delete()

    def test_get_denied(self):
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.get(reverse("adminsec:termsandconditions-create"))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))

    def test_post_denied(self):
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.post(reverse("adminsec:termsandconditions-create"), self.terms)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))
        self.assertEqual(TermsAndConditions.objects.count(), 0)


class TestTermsAndConditionsUpdateViewPermissions(TestViewBase):
    """Tests for TermsAndConditionsUpdateView."""

    def setUp(self):
        super().setUp()
        self.terms = TermsAndConditionsFactory()
        self.new_terms = {
            "title": "Terms and Conditions",
            "text": "Updated",
            "audience": TERMS_AUDIENCE_USER,
        }

    def test_get_allowed(self):
        for user in [self.user_hpcadmin, self.superuser]:
            with self.login(user):
                response = self.client.get(reverse(
                    "adminsec:termsandconditions-update",
                    kwargs={"termsandconditions": self.terms.uuid},
                ))
                self.assertEqual(response.status_code, 200)
                self.assertIsNotNone(response.context["form"])

    def test_post_allowed(self):
        self.assertEqual(TermsAndConditions.objects.count(), 1)
        initial_text = TermsAndConditions.objects.first().text
        for user in [self.user_hpcadmin, self.superuser]:
            with self.login(user):
                self.assertEqual(TermsAndConditions.objects.first().text, initial_text)
                response = self.client.post(
                    reverse("adminsec:termsandconditions-update",
                    kwargs={"termsandconditions": self.terms.uuid},
                            ),
                    self.new_terms,
                )
                self.assertRedirects(
                    response,
                    reverse("adminsec:termsandconditions-list"),
                )
                self.assertEqual(TermsAndConditions.objects.count(), 1)
                tac = TermsAndConditions.objects.first()
                self.assertEqual(tac.text, "Updated")
                tac.text = initial_text
                tac.save()

    def test_get_denied(self):
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.get(reverse("adminsec:termsandconditions-update",
                    kwargs={"termsandconditions": self.terms.uuid},
                                                   ))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))

    def test_post_denied(self):
        initial_text = TermsAndConditions.objects.first().text
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.post(reverse("adminsec:termsandconditions-update",
                    kwargs={"termsandconditions": self.terms.uuid},
                                                    ), self.new_terms)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))
        self.assertEqual(TermsAndConditions.objects.first().text, initial_text)


class TestTermsAndConditionsDeleteViewPermissions(TestViewBase):
    """Tests for TermsAndConditionsDeleteView."""

    def setUp(self):
        super().setUp()
        self.terms = TermsAndConditionsFactory()

    def test_get_allowed(self):
        self.assertEqual(TermsAndConditions.objects.count(), 1)
        for user in [self.user_hpcadmin, self.superuser]:
            with self.login(user):
                response = self.client.get(reverse(
                    "adminsec:termsandconditions-delete",
                    kwargs={"termsandconditions": self.terms.uuid},
                ))
                self.assertEqual(response.status_code, 200)
                self.assertIsNotNone(response.context["form"])
                self.assertEqual(TermsAndConditions.objects.count(), 1)

    def test_post_allowed(self):
        self.assertEqual(TermsAndConditions.objects.count(), 1)
        for user in [self.user_hpcadmin, self.superuser]:
            with self.login(user):
                response = self.client.post(
                    reverse("adminsec:termsandconditions-delete",
                    kwargs={"termsandconditions": self.terms.uuid},
                            ),
                )
                self.assertRedirects(
                    response,
                    reverse("adminsec:termsandconditions-list"),
                )
                self.assertEqual(TermsAndConditions.objects.count(), 0)
                self.terms = TermsAndConditionsFactory()

    def test_get_denied(self):
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.get(reverse("adminsec:termsandconditions-delete",
                    kwargs={"termsandconditions": self.terms.uuid},
                                                   ))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))

    def test_post_denied(self):
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.post(reverse("adminsec:termsandconditions-delete",
                    kwargs={"termsandconditions": self.terms.uuid},
                                                    ))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))
        self.assertEqual(TermsAndConditions.objects.count(), 1)


class TestTermsAndConditionsPublishViewPermissions(TestViewBase):
    """Tests for TermsAndConditionsPublishView."""

    def setUp(self):
        super().setUp()

    def test_get_denied(self):
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.get(
                    reverse(
                        "adminsec:termsandconditions-publish",
                    )
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))

    def test_post_denied(self):
        for user in [self.user, self.user_owner, self.user_member]:
            with self.login(user):
                response = self.client.post(
                    reverse(
                        "adminsec:termsandconditions-publish",
                    )
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("home"))
