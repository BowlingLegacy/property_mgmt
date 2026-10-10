from datetime import datetime, timezone as datetime_timezone

from django.test import TestCase
from django.urls import reverse

from .models import HousingApplication, Property, User


class OwnerCountAndApplicationTimeTests(TestCase):
    def setUp(self):
        Property.objects.all().delete()
        self.admin = User.objects.create_user(
            username="dashboard-admin",
            email="admin@example.com",
            password="StrongPass123!",
            role="admin",
            is_staff=True,
        )
        self.owner = User.objects.create_user(
            username="portfolio-owner",
            email="owner@example.com",
            password="StrongPass123!",
            role="property_owner",
        )
        self.first_property = Property.objects.create(
            name="First Owner Property",
            owner_email=self.owner.email,
        )
        self.second_property = Property.objects.create(
            name="Second Owner Property",
            owner_email=self.owner.email,
        )
        self.client.login(username=self.admin.username, password="StrongPass123!")

    def test_dashboard_counts_one_owner_account_and_two_properties(self):
        User.objects.create_user(
            username="unused-owner-account",
            email="unused-owner@example.com",
            password="StrongPass123!",
            role="property_owner",
        )

        response = self.client.get(reverse("superadmin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["owner_count"], 1)
        self.assertEqual(response.context["properties"].count(), 2)
        self.assertContains(response, "Property owner accounts")

    def test_application_submission_times_use_pacific_time_with_dst(self):
        application = HousingApplication.objects.create(
            property=self.first_property,
            full_name="Pacific Time Applicant",
            phone="555-0100",
            email="applicant@example.com",
            age=30,
            income_source="Employment",
            monthly_income="4000.00",
            housing_need="Housing",
            application_folder="waiting",
        )

        application.created_at = datetime(2026, 1, 15, 12, 0, tzinfo=datetime_timezone.utc)
        application.save(update_fields=["created_at"])
        winter_response = self.client.get(reverse("landlord_application_folder", args=["waiting"]))
        self.assertContains(winter_response, "Jan 15, 2026, 4:00 AM")

        application.created_at = datetime(2026, 7, 15, 12, 0, tzinfo=datetime_timezone.utc)
        application.save(update_fields=["created_at"])
        summer_response = self.client.get(reverse("landlord_application_folder", args=["waiting"]))
        self.assertContains(summer_response, "Jul 15, 2026, 5:00 AM")
