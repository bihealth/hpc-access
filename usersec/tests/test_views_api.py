from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usersec.models import HpcUser
from usersec.tests.factories import HpcUserFactory


class TestHpcUserLookupApiView(APITestCase):
    """Tests for HpcUserLookupApiView."""

    def test_list_empty(self):
        url = reverse("usersec:api-hpcuser-lookup")
        expected = []
        response = self.client.get(url + "?q=user")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), expected)

    def test_list_all(self):
        HpcUserFactory.create_batch(3)
        url = reverse("usersec:api-hpcuser-lookup")
        response = self.client.get(url + "?q=user")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = HpcUser.objects.all()
        expected = [
            {
                "full_name": users[0].user.name,
                "id": users[0].id,
                "primary_group": users[0].primary_group.name,
                "username": users[0].username,
            },
            {
                "full_name": users[1].user.name,
                "id": users[1].id,
                "primary_group": users[1].primary_group.name,
                "username": users[1].username,
            },
            {
                "full_name": users[2].user.name,
                "id": users[2].id,
                "primary_group": users[2].primary_group.name,
                "username": users[2].username,
            },
        ]

        self.assertEqual(response.json(), expected)

    def test_list_single(self):
        HpcUserFactory.create_batch(3)
        url = reverse("usersec:api-hpcuser-lookup")
        response = self.client.get(url + f"?q={HpcUser.objects.first().username}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = HpcUser.objects.all()
        expected = [
            {
                "full_name": users[0].user.name,
                "id": users[0].id,
                "primary_group": users[0].primary_group.name,
                "username": users[0].username,
            },
        ]

        self.assertEqual(response.json(), expected)
