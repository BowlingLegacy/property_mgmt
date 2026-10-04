from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import HousingApplication, Payment, Property, User


class FormerTenantPaymentTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            username="former-payment-landlord",
            email="former-payment-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        self.property = Property.objects.create(
            name="Former Payment Property",
            landlord_email=self.landlord.email,
        )
        self.former = HousingApplication.objects.create(
            property=self.property,
            user=User.objects.create_user(
                username="mitchell-brent-payment",
                password="StrongPass123!",
                role="tenant",
            ),
            full_name="Mitchell Brent",
            phone="555-0140",
            email="mitchell-payment@example.com",
            age=50,
            space_label="P",
            lease_start_date=date(2026, 8, 3),
            monthly_rent=Decimal("650.00"),
            balance=Decimal("325.00"),
            utility_monthly=Decimal("55.00"),
            utility_balance=Decimal("0.00"),
            tenancy_status="former",
            move_out_date=date(2026, 10, 15),
            former_tenant_archived_at=timezone.now(),
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Former resident.",
        )
        self.client.login(username=self.landlord.username, password="StrongPass123!")

    def test_former_tenant_with_balance_has_record_payment_action(self):
        response = self.client.get(reverse("former_tenant_files"))

        self.assertContains(response, reverse("landlord_dashboard"))
        self.assertContains(response, "Landlord Dashboard")
        self.assertContains(response, "Record Payment")
        self.assertContains(response, f"application={self.former.id}")

    def test_prorated_final_rent_payment_is_accepted_as_paid_in_full(self):
        payment_url = (
            f"{reverse('record_manual_payment')}?application={self.former.id}"
            "&return=former_tenants"
        )
        get_response = self.client.get(payment_url)

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.context["form"].initial["amount"], Decimal("325.00"))

        response = self.client.post(payment_url, {
            "application": self.former.id,
            "payment_type": "rent",
            "payment_method": "cash",
            "amount": "325.00",
            "service_month": "2026-10",
            "months_covered": "1",
            "description": "October move-out prorated rent paid in full",
            "return_to": "former_tenants",
        })

        self.assertRedirects(response, reverse("former_tenant_files"))
        self.former.refresh_from_db()
        self.assertEqual(self.former.balance, Decimal("0.00"))
        payment = Payment.objects.get(application=self.former, payment_type="rent")
        self.assertEqual(payment.amount, Decimal("325.00"))
        self.assertEqual(payment.service_month, date(2026, 10, 1))
        self.assertEqual(payment.status, "completed")

        list_response = self.client.get(reverse("former_tenant_files"))
        self.assertNotContains(
            list_response,
            f"{reverse('record_manual_payment')}?application={self.former.id}&amp;return=former_tenants",
        )
