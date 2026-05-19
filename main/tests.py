from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import HousingApplication, Payment, Property, User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    STRIPE_SECRET_KEY="sk_test_local",
    STRIPE_PUBLIC_KEY="pk_test_local",
    STRIPE_WEBHOOK_SECRET="whsec_local",
)
class LiveFlowTests(TestCase):
    def application_payload(self):
        return {
            "full_name": "New Applicant",
            "phone": "555-0100",
            "email": "applicant@example.com",
            "age": "42",
            "income_source": "Employment",
            "monthly_income": "2500.00",
            "housing_need": "Needs a vacant room this month.",
            "sobriety_acknowledgment": "on",
            "unconditional_regard_acknowledgment": "on",
        }

    def test_application_from_property_page_keeps_property_assignment(self):
        property_obj = Property.objects.create(name="Painted Lady Inn")

        response = self.client.post(
            f"{reverse('apply')}?property={property_obj.id}",
            self.application_payload(),
        )

        self.assertEqual(response.status_code, 302)

        application = HousingApplication.objects.get(email="applicant@example.com")
        self.assertEqual(application.property, property_obj)

    def test_printable_application_includes_full_intake_details(self):
        application = HousingApplication.objects.create(
            full_name="Detailed Applicant",
            phone="555-0100",
            email="detailed@example.com",
            age=42,
            current_address="123 Current Street",
            current_address_length="Two years",
            previous_address_1="Shared housing in Salem",
            previous_address_1_length="Needed stable sober housing",
            income_source="Employment and benefits",
            monthly_income=Decimal("2500.00"),
            employer_name="Local Employer",
            employment_length="18 months",
            previous_evictions="No evictions, one late payment history note.",
            in_recovery=True,
            drug_of_choice="Needs recovery-friendly support.",
            on_parole=True,
            parole_officer_name="Officer Smith",
            parole_officer_phone="555-0199",
            felony_history="Applicant disclosed past conviction context.",
            odoc_time_served=True,
            reference_1_name="Reference One",
            reference_1_phone="555-0111",
            reference_1_relationship="Case manager",
            reference_2_name="Reference Two",
            reference_2_phone="555-0222",
            reference_2_relationship="Employer",
            housing_need="Needs a vacant room this month.",
            sobriety_acknowledgment=True,
            unconditional_regard_acknowledgment=True,
        )

        response = self.client.get(reverse("application_detail", args=[application.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shared housing in Salem")
        self.assertContains(response, "No evictions, one late payment history note.")
        self.assertContains(response, "Employment and benefits")
        self.assertContains(response, "Officer Smith")
        self.assertContains(response, "Reference One")
        self.assertContains(response, "Needs a vacant room this month.")

    def test_invite_code_allows_resident_to_create_account_and_pay(self):
        temp_user = User.objects.create_user(
            username="new-applicant-1",
            email="applicant@example.com",
            password=None,
            role="tenant",
        )
        application = HousingApplication.objects.create(
            user=temp_user,
            full_name="New Applicant",
            phone="555-0100",
            email="applicant@example.com",
            age=42,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Needs a room.",
            balance=Decimal("900.00"),
        )

        response = self.client.post(reverse("enter_invite_code"), {
            "invite_code": temp_user.invite_code,
        })

        self.assertRedirects(response, reverse("signup"))

        response = self.client.post(reverse("signup"), {
            "username": "resident",
            "email": "applicant@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(response, reverse("tenant_dashboard"))

        application.refresh_from_db()
        self.assertEqual(application.user.username, "resident")
        self.assertFalse(User.objects.filter(id=temp_user.id).exists())

    def test_approving_application_sends_invite_email(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        application = HousingApplication.objects.create(
            full_name="Email Applicant",
            phone="555-0100",
            email="email-applicant@example.com",
            age=42,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Needs a room.",
        )

        self.client.login(username="staff", password="StrongPass123!")

        response = self.client.post(
            f"{reverse('landlord_create_tenant')}?application={application.id}",
            {
                "monthly_rent": "900.00",
                "balance": "900.00",
                "rent_due_day": "1",
                "deposit_required": "450.00",
                "deposit_paid": "0.00",
                "utility_monthly": "66.00",
                "utility_balance": "0.00",
                "space_type": "Room",
                "space_label": "3",
            },
        )

        self.assertEqual(response.status_code, 200)

        application.refresh_from_db()
        self.assertIsNotNone(application.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(application.user.invite_code, mail.outbox[0].body)
        self.assertIn("https://bowlinglegacy.com/enter-invite-code/", mail.outbox[0].body)

    @patch("main.views.stripe.checkout.Session.create")
    def test_resident_can_start_own_rent_payment(self, create_session):
        create_session.return_value.id = "cs_test_123"
        create_session.return_value.url = "https://checkout.stripe.test/session"

        user = User.objects.create_user(
            username="resident",
            email="resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        application = HousingApplication.objects.create(
            user=user,
            full_name="Resident",
            phone="555-0101",
            email="resident@example.com",
            age=50,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
            balance=Decimal("900.00"),
        )

        self.client.login(username="resident", password="StrongPass123!")

        response = self.client.get(reverse("pay_by_type", args=[application.id, "rent"]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://checkout.stripe.test/session")
        self.assertEqual(Payment.objects.filter(application=application, status="pending").count(), 1)

    def test_resident_cannot_pay_another_resident_account(self):
        user = User.objects.create_user(
            username="resident",
            email="resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        HousingApplication.objects.create(
            user=user,
            full_name="Resident",
            phone="555-0101",
            email="resident@example.com",
            age=50,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
            balance=Decimal("900.00"),
        )
        other_application = HousingApplication.objects.create(
            user=other_user,
            full_name="Other Resident",
            phone="555-0102",
            email="other@example.com",
            age=51,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
            balance=Decimal("900.00"),
        )

        self.client.login(username="resident", password="StrongPass123!")

        response = self.client.get(reverse("pay_by_type", args=[other_application.id, "rent"]))

        self.assertEqual(response.status_code, 403)
