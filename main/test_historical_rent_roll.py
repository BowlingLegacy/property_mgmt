from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from main.models import HousingApplication, Property, User


class HistoricalRentRollTests(TestCase):
    @patch("main.views.timezone.localdate", return_value=date(2026, 7, 17))
    def test_keeps_active_resident_without_portal_or_monthly_payment(self, _mocked_localdate):
        landlord = User.objects.create_user(
            username="historical-roster-landlord",
            email="historical-roster@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(
            name="Historical Roster Property",
            landlord_email=landlord.email,
        )
        HousingApplication.objects.create(
            property=property_obj,
            full_name="Ray Ferro",
            phone="555-0625",
            email="",
            age=64,
            space_label="O",
            lease_start_date=date(2026, 1, 1),
            monthly_rent=Decimal("506.00"),
            utility_monthly=Decimal("55.00"),
            income_source="Fixed income",
            monthly_income=Decimal("2400.00"),
            housing_need="Current resident.",
        )

        self.client.login(username="historical-roster-landlord", password="StrongPass123!")
        response = self.client.get(f"{reverse('rent_roll')}?month=2026-05")

        row = next(row for row in response.context["rows"] if row["resident"] == "Ray Ferro")
        self.assertEqual(row["room"], "O")
        self.assertEqual(row["monthly_rent"], Decimal("506.00"))
