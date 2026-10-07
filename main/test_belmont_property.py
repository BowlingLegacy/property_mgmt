import importlib

from django.apps import apps as django_apps
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Property


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class BelmontPropertyTests(TestCase):
    def setUp(self):
        migration = importlib.import_module("main.migrations.0080_add_belmont_property")
        migration.add_belmont_property(django_apps, None)
        history_migration = importlib.import_module("main.migrations.0081_add_belmont_family_history")
        history_migration.add_belmont_family_history(django_apps, None)
        date_migration = importlib.import_module("main.migrations.0083_clarify_jeffery_bowling_dates")
        date_migration.clarify_jeffery_bowling_dates(django_apps, None)
        correction_migration = importlib.import_module("main.migrations.0084_correct_jeffery_bowling_year")
        correction_migration.correct_jeffery_bowling_year(django_apps, None)
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
        self.assertContains(response, "Jeffery R. Bowling")
        self.assertContains(response, "more than twenty years")
        self.assertContains(response, "forty years old")
        self.assertContains(response, "forty-first birthday")
        self.assertContains(response, "September 19, 1969")
        self.assertContains(response, "July 2010")
        self.assertContains(response, "September 19, 2010")
        self.assertNotContains(response, "July 2009")
        self.assertNotContains(response, "passed away suddenly in July at")
        self.assertContains(response, "honor Jeffery&#x27;s memory", html=False)
        self.assertContains(response, "/static/property_photos/belmont-front-privacy-safe.png")
        self.assertContains(response, "/static/property_photos/belmont-side-privacy-safe.png")
        self.assertNotContains(response, "/media/property_photos/belmont-front-privacy-safe.png")
        self.assertNotContains(response, "Apply / Join Waitlist")
        self.assertNotContains(response, "Sober Living")
        self.assertNotContains(response, "$650.00")

    def test_belmont_list_card_uses_deploy_safe_static_photo(self):
        response = self.client.get(reverse("properties_list"))

        self.assertContains(response, "/static/property_photos/belmont-front-privacy-safe.png")
        self.assertNotContains(response, "/media/property_photos/belmont-front-privacy-safe.png")
