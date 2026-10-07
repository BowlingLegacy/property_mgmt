import importlib

from django.apps import apps as django_apps
from django.test import TestCase
from django.urls import reverse

from .models import Property


class BelmontPropertyTests(TestCase):
    def setUp(self):
        migration = importlib.import_module("main.migrations.0080_add_belmont_property")
        migration.add_belmont_property(django_apps, None)
        self.property = Property.objects.get(name="Belmont")

    def test_belmont_profile_is_privacy_safe_and_currently_occupied(self):
        self.assertEqual(self.property.address, "Santa Clara area, Eugene, Oregon")
        self.assertEqual(self.property.availability_status, "full")
        self.assertIsNone(self.property.rent_amount)
        self.assertEqual(self.property.images.count(), 1)

        response = self.client.get(reverse("property_detail", args=[self.property.id]))

        self.assertContains(response, "Belmont")
        self.assertContains(response, "Both homes are currently occupied")
        self.assertContains(response, "Two 3-bedroom, 1-bath homes")
        self.assertContains(response, "Residents pay power, utilities, and garbage")
        self.assertContains(response, "Not publicly listed")
        self.assertContains(response, "Extra-Large Backyard")
        self.assertNotContains(response, "Apply / Join Waitlist")
        self.assertNotContains(response, "Sober Living")
        self.assertNotContains(response, "$650.00")
