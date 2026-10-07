import importlib
from datetime import date

from django.apps import apps as django_apps
from django.test import TestCase
from django.urls import reverse

from .models import Property


class PaintedLadyPropertyAvailabilityTests(TestCase):
    def test_october_availability_update_appears_on_property_detail(self):
        property_obj = Property.objects.create(
            name="The Painted Lady Inn",
            unit_size="Shared room",
            availability_status="full",
            availability_message="Currently full",
        )
        migration = importlib.import_module(
            "main.migrations.0079_update_painted_lady_october_availability"
        )

        migration.update_painted_lady_availability(django_apps, None)
        property_obj.refresh_from_db()

        self.assertEqual(property_obj.unit_size, "Single occupancy")
        self.assertEqual(property_obj.available_date, date(2026, 10, 15))
        self.assertEqual(property_obj.availability_status, "waitlist")
        self.assertEqual(
            property_obj.availability_message,
            "Single-occupancy room available October 15, 2026",
        )

        response = self.client.get(reverse("property_detail", args=[property_obj.id]))
        self.assertContains(response, "Waitlist Open")
        self.assertContains(response, "Single-occupancy room available October 15, 2026")
        self.assertContains(response, "Single occupancy")
        self.assertContains(response, "Oct 15, 2026")
