from django.test import TestCase
from django.urls import reverse

from .models import Property


class PropertyVisibilityTests(TestCase):
    def setUp(self):
        self.public_property = Property.objects.create(name="Public Home")
        self.hidden_property = Property.objects.create(name="Hidden Home", is_public=False)

    def test_hidden_property_is_omitted_from_public_lists(self):
        for route in ("home", "properties_list"):
            response = self.client.get(reverse(route))
            self.assertContains(response, self.public_property.name)
            self.assertNotContains(response, self.hidden_property.name)

    def test_hidden_property_detail_returns_not_found(self):
        response = self.client.get(reverse("property_detail", args=[self.hidden_property.id]))
        self.assertEqual(response.status_code, 404)

    def test_existing_properties_remain_public_by_default(self):
        self.assertTrue(self.public_property.is_public)
        response = self.client.get(reverse("property_detail", args=[self.public_property.id]))
        self.assertEqual(response.status_code, 200)
