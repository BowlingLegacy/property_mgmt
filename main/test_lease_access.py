from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import HousingApplication, Property, SignedDocument, User


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class LeaseAccessTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            username="lease-landlord",
            email="lease-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        self.property = Property.objects.create(
            name="Mitchell Lease Property",
            landlord_email=self.landlord.email,
        )
        self.application = HousingApplication.objects.create(
            property=self.property,
            full_name="Mitchell Brent",
            phone="5550112233",
            email="mitchell@example.com",
            age=50,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
        )
        self.lease = SignedDocument.objects.create(
            application=self.application,
            document_type="lease",
            title="Resident Lease Agreement",
        )
        self.client.login(username="lease-landlord", password="StrongPass123!")

    def test_landlord_can_open_lease_from_inspected_resident_inbox(self):
        inbox_url = f"{reverse('resident_inbox')}?resident={self.application.id}"
        lease_url = f"{reverse('onboarding_document', args=[self.lease.id])}?resident={self.application.id}"

        inbox_response = self.client.get(inbox_url)
        self.assertContains(inbox_response, lease_url)

        lease_response = self.client.get(lease_url)
        self.assertEqual(lease_response.status_code, 200)
        self.assertEqual(lease_response.context["signed_document"], self.lease)
        self.assertContains(lease_response, "Mitchell Brent")

    def test_landlord_cannot_open_lease_for_unmanaged_property(self):
        other_property = Property.objects.create(name="Unmanaged Property")
        other_application = HousingApplication.objects.create(
            property=other_property,
            full_name="Other Resident",
            phone="5550112244",
            age=40,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        other_lease = SignedDocument.objects.create(
            application=other_application,
            document_type="lease",
            title="Other Lease",
        )

        response = self.client.get(
            f"{reverse('onboarding_document', args=[other_lease.id])}?resident={other_application.id}"
        )

        self.assertEqual(response.status_code, 404)
