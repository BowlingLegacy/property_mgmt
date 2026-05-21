from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib import admin
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import ApplicantDocument, BlogComment, BlogPost, ExistingResidentIntake, HousingApplication, LandlordIntake, Payment, Property, PropertyOwnerIntake, ResidentMessage, SignedDocument, User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    STRIPE_SECRET_KEY="sk_test_local",
    STRIPE_PUBLIC_KEY="pk_test_local",
    STRIPE_WEBHOOK_SECRET="whsec_local",
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
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
        temp_user.refresh_invite_code()
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

    def test_invite_code_expires_after_30_minutes(self):
        temp_user = User.objects.create_user(
            username="expired-applicant",
            email="expired@example.com",
            password=None,
            role="tenant",
        )
        temp_user.refresh_invite_code()
        temp_user.invite_code_created_at = timezone.now() - timezone.timedelta(minutes=31)
        temp_user.save(update_fields=["invite_code_created_at"])
        HousingApplication.objects.create(
            user=temp_user,
            full_name="Expired Applicant",
            phone="555-0100",
            email="expired@example.com",
            age=42,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Needs a room.",
        )

        response = self.client.post(reverse("enter_invite_code"), {
            "invite_code": temp_user.invite_code,
        })

        self.assertRedirects(response, reverse("request_invite_code"))

    def test_property_owner_invite_code_creates_owner_login(self):
        temp_user = User.objects.create_user(
            username="pending-owner",
            email="new-owner@example.com",
            password=None,
            role="property_owner",
        )
        temp_user.refresh_invite_code()
        intake = PropertyOwnerIntake.objects.create(
            full_name="New Owner",
            email="new-owner@example.com",
            phone="555-0130",
            user=temp_user,
            status="invited",
        )

        response = self.client.post(reverse("enter_invite_code"), {"invite_code": temp_user.invite_code})
        self.assertRedirects(response, reverse("signup"))

        response = self.client.post(reverse("signup"), {
            "username": "new-owner",
            "email": "new-owner@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(response, reverse("property_owner_dashboard"))
        intake.refresh_from_db()
        self.assertEqual(intake.user.username, "new-owner")
        self.assertEqual(intake.status, "registered")
        self.assertFalse(User.objects.filter(id=temp_user.id).exists())

    def test_landlord_invite_code_creates_staff_landlord_login(self):
        temp_user = User.objects.create_user(
            username="pending-landlord",
            email="new-landlord@example.com",
            password=None,
            role="landlord",
            is_staff=True,
        )
        temp_user.refresh_invite_code()
        intake = LandlordIntake.objects.create(
            full_name="New Landlord",
            email="new-landlord@example.com",
            phone="555-0131",
            user=temp_user,
            status="invited",
        )

        response = self.client.post(reverse("enter_invite_code"), {"invite_code": temp_user.invite_code})
        self.assertRedirects(response, reverse("signup"))

        response = self.client.post(reverse("signup"), {
            "full_name": "New Landlord",
            "phone": "555-0131",
            "address": "12 Landlord Lane",
            "username": "new-landlord",
            "email": "new-landlord@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(response, reverse("landlord_dashboard"))
        intake.refresh_from_db()
        self.assertEqual(intake.user.username, "new-landlord")
        self.assertEqual(intake.full_name, "New Landlord")
        self.assertEqual(intake.phone, "555-0131")
        self.assertEqual(intake.address, "12 Landlord Lane")
        self.assertTrue(intake.user.is_staff)
        self.assertEqual(intake.status, "registered")

    def test_unregistered_user_can_request_replacement_invite_code(self):
        temp_user = User.objects.create_user(
            username="replacement-applicant",
            email="replacement@example.com",
            password=None,
            role="tenant",
        )
        temp_user.refresh_invite_code()
        old_code = temp_user.invite_code
        HousingApplication.objects.create(
            user=temp_user,
            full_name="Replacement Applicant",
            phone="555-0100",
            email="replacement@example.com",
            age=42,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Needs a room.",
        )

        response = self.client.post(reverse("request_invite_code"), {
            "email": "replacement@example.com",
        })

        self.assertRedirects(response, reverse("enter_invite_code"))
        temp_user.refresh_from_db()
        self.assertNotEqual(temp_user.invite_code, old_code)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(temp_user.invite_code, mail.outbox[0].body)

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
                "deposit_payment_plan": "ninety_day_plan",
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
        self.assertEqual(application.deposit_payment_plan, "ninety_day_plan")
        self.assertEqual(
            set(application.signed_documents.values_list("document_type", flat=True)),
            {"lease", "emergency_contact", "painted_lady_acknowledgment"},
        )
        lease = application.signed_documents.get(document_type="lease")
        self.assertEqual(lease.resident_name, "Email Applicant")
        self.assertEqual(lease.monthly_rent, Decimal("900.00"))
        self.assertEqual(lease.security_deposit, Decimal("450.00"))
        self.assertEqual(lease.utility_fee, Decimal("66.00"))
        self.assertEqual(lease.landlord_signature, "Michael Bowling")
        self.assertEqual(lease.deposit_payment_plan, "ninety_day_plan")

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
        create_session.assert_called_once()
        self.assertEqual(
            create_session.call_args.kwargs["payment_method_types"],
            ["card", "cashapp"],
        )
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

    def test_staff_can_record_manual_bank_transfer_rent_payment(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        application = HousingApplication.objects.create(
            full_name="Manual Pay Resident",
            phone="555-0103",
            email="manual@example.com",
            age=44,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
            balance=Decimal("900.00"),
        )

        self.client.login(username="staff", password="StrongPass123!")

        response = self.client.post(reverse("record_manual_payment"), {
            "application": application.id,
            "payment_type": "rent",
            "payment_method": "bank_transfer",
            "amount": "250.00",
            "reference_number": "BANK-123",
            "description": "Same-bank transfer",
            "notes": "Confirmed in bank portal.",
        })

        payment = Payment.objects.get(application=application)
        self.assertRedirects(response, reverse("payment_receipt", args=[payment.id]))

        application.refresh_from_db()
        self.assertEqual(application.balance, Decimal("650.00"))

        self.assertEqual(payment.status, "completed")
        self.assertEqual(payment.payment_method, "bank_transfer")
        self.assertEqual(payment.reference_number, "BANK-123")
        self.assertEqual(payment.recorded_by, staff_user)

        response = self.client.get(reverse("payment_receipt", args=[payment.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment Receipt")
        self.assertContains(response, "BANK-123")

    def test_staff_can_record_manual_cashapp_deposit_payment(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        application = HousingApplication.objects.create(
            full_name="Cash App Resident",
            phone="555-0104",
            email="cashapp@example.com",
            age=45,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
            deposit_required=Decimal("450.00"),
            deposit_paid=Decimal("100.00"),
        )

        self.client.login(username="staff", password="StrongPass123!")

        response = self.client.post(reverse("record_manual_payment"), {
            "application": application.id,
            "payment_type": "deposit",
            "payment_method": "cashapp",
            "amount": "200.00",
            "reference_number": "CashApp $resident",
            "description": "Cash App deposit payment",
        })

        payment = Payment.objects.get(application=application)
        self.assertRedirects(response, reverse("payment_receipt", args=[payment.id]))

        application.refresh_from_db()
        self.assertEqual(application.deposit_paid, Decimal("300.00"))

        self.assertEqual(payment.payment_method, "cashapp")
        self.assertEqual(payment.recorded_by, staff_user)

    def test_landlord_dashboard_highlights_new_items(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        application = HousingApplication.objects.create(
            full_name="New Queue Resident",
            phone="555-0105",
            email="queue@example.com",
            age=46,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Needs review.",
        )
        ResidentMessage.objects.create(
            application=application,
            message_type="maintenance",
            subject="New request",
            message="Please review.",
            status="submitted",
        )
        ApplicantDocument.objects.create(
            application=application,
            document_type="id",
            name="Uploaded ID",
            file="applicant_documents/id.pdf",
            status="uploaded",
            landlord_notified=False,
        )

        self.client.login(username="staff", password="StrongPass123!")

        response = self.client.get(reverse("landlord_attention"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Needs Attention")
        self.assertContains(response, "New Queue Resident")
        self.assertContains(response, "New request")
        self.assertContains(response, "Uploaded ID")
        self.assertContains(response, "Mark Reviewed")

    def test_create_tenant_without_application_redirects_to_dashboard(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )

        self.client.login(username="staff", password="StrongPass123!")

        response = self.client.get(reverse("landlord_create_tenant"))

        self.assertRedirects(response, reverse("landlord_dashboard"))

    def test_resident_can_sign_emergency_contact_and_locked_copy_remains_viewable(self):
        user = User.objects.create_user(
            username="resident-doc",
            email="resident-doc@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        application = HousingApplication.objects.create(
            user=user,
            full_name="Document Resident",
            phone="555-0110",
            email="resident-doc@example.com",
            age=51,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
        )
        signed_document = SignedDocument.objects.create(
            application=application,
            document_type="emergency_contact",
            title="Emergency Contact Sheet",
        )

        self.client.login(username="resident-doc", password="StrongPass123!")

        response = self.client.post(reverse("submit_onboarding_document", args=[signed_document.id]), {
            "emergency_contact_name": "Emergency Person",
            "emergency_contact_phone": "555-0198",
            "emergency_contact_relationship": "Friend",
            "resident_signature": "Document Resident",
            "signature_agreement": "on",
        })

        self.assertRedirects(response, reverse("tenant_dashboard"))
        signed_document.refresh_from_db()
        self.assertTrue(signed_document.locked)
        self.assertEqual(signed_document.emergency_contact_name, "Emergency Person")

        response = self.client.get(reverse("onboarding_document", args=[signed_document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "viewable but no longer editable")
        self.assertContains(response, "Emergency Person")

    def test_resident_can_upload_profile_photo(self):
        user = User.objects.create_user(
            username="photo-resident",
            email="photo-resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        application = HousingApplication.objects.create(
            user=user,
            full_name="Photo Resident",
            phone="555-0111",
            email="photo-resident@example.com",
            age=52,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
        )
        image = SimpleUploadedFile(
            "resident.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )

        self.client.login(username="photo-resident", password="StrongPass123!")

        response = self.client.post(reverse("update_resident_profile_photo"), {
            "profile_photo": image,
        })

        self.assertRedirects(response, reverse("tenant_dashboard"))
        application.refresh_from_db()
        self.assertTrue(application.profile_photo.name)

    def test_superadmin_can_inspect_tenant_dashboard_by_resident_file(self):
        superuser = User.objects.create_user(
            username="superadmin",
            email="super@example.com",
            password="StrongPass123!",
            role="admin",
            is_staff=True,
        )
        application = HousingApplication.objects.create(
            full_name="Inspect Resident",
            phone="555-0112",
            email="inspect@example.com",
            age=53,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Current resident.",
        )

        self.client.login(username="superadmin", password="StrongPass123!")

        response = self.client.get(f"{reverse('tenant_dashboard')}?resident={application.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inspect Resident")
        self.assertContains(response, "Back to Super Admin Dashboard")

    def test_superadmin_owners_page_lists_properties_without_owner_email(self):
        User.objects.create_user(
            username="superadmin",
            email="super@example.com",
            password="StrongPass123!",
            role="admin",
            is_staff=True,
        )
        Property.objects.create(name="Painted Lady Inn", owner_email="")

        self.client.login(username="superadmin", password="StrongPass123!")

        response = self.client.get(reverse("superadmin_owners"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unassigned Owner")
        self.assertContains(response, "Painted Lady Inn")

    def test_property_owner_role_can_open_empty_owner_dashboard(self):
        User.objects.create_user(
            username="portfolio-owner",
            email="owner@example.com",
            password="StrongPass123!",
            role="property_owner",
        )

        response = self.client.post(reverse("login"), {
            "username": "portfolio-owner",
            "password": "StrongPass123!",
        })

        self.assertRedirects(response, reverse("property_owner_dashboard"))

        dashboard_response = self.client.get(reverse("property_owner_dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "No properties are connected to this owner yet.")

    def test_property_owner_intake_questionnaire_saves_system_needs(self):
        form_response = self.client.get(reverse("property_owner_intake"))
        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, "Tell us what your dashboard needs to do.")
        self.assertContains(form_response, "Submit Questionnaire")

        response = self.client.post(reverse("property_owner_intake"), {
            "full_name": "Portfolio Owner",
            "company_name": "North Street Holdings",
            "email": "portfolio@example.com",
            "phone": "555-0191",
            "property_count": "4",
            "total_units": "120",
            "property_types": ["multifamily", "commercial"],
            "current_software": "QuickBooks and spreadsheets",
            "needs_rent_collection": "on",
            "needs_accounting": "on",
            "needs_data_migration": "on",
            "dashboard_goals": "Show NOI and rent collection by property.",
        })

        self.assertRedirects(response, reverse("property_owner_intake_success"))
        intake = PropertyOwnerIntake.objects.get(email="portfolio@example.com")
        self.assertEqual(intake.property_count, 4)
        self.assertEqual(intake.total_units, 120)
        self.assertEqual(intake.property_types, "multifamily,commercial")
        self.assertTrue(intake.needs_accounting)
        self.assertTrue(intake.needs_data_migration)

    def test_existing_resident_intake_button_opens_for_new_property_and_saves_profile(self):
        property_obj = Property.objects.create(name="Painted Lady Inn")

        property_response = self.client.get(reverse("property_detail", args=[property_obj.id]))
        self.assertEqual(property_response.status_code, 200)
        self.assertContains(property_response, "Existing Resident Profile")

        response = self.client.post(reverse("existing_resident_intake", args=[property_obj.id]), {
            "first_name": "Existing",
            "middle_name": "R",
            "last_name": "Resident",
            "email": "existing@example.com",
            "phone": "555-0195",
            "has_valid_odl": "on",
            "years_at_residence": "3",
            "move_in_month": "2023-07",
        })

        self.assertRedirects(response, reverse("existing_resident_intake_success", args=[property_obj.id]))
        intake = ExistingResidentIntake.objects.get(email="existing@example.com")
        self.assertEqual(intake.property, property_obj)
        self.assertEqual(intake.full_name(), "Existing R Resident")
        self.assertEqual(intake.move_in_month, "2023-07")
        self.assertTrue(intake.has_valid_odl)

    def test_existing_resident_intake_closes_after_property_window(self):
        property_obj = Property.objects.create(name="Older Property")
        property_obj.created_at = timezone.now() - timezone.timedelta(days=31)
        property_obj.save(update_fields=["created_at"])

        property_response = self.client.get(reverse("property_detail", args=[property_obj.id]))
        self.assertNotContains(property_response, "Existing Resident Profile")

        intake_response = self.client.get(reverse("existing_resident_intake", args=[property_obj.id]))
        self.assertRedirects(intake_response, reverse("property_detail", args=[property_obj.id]))

    def test_homepage_shows_painted_lady_profile_setup_during_intake_window(self):
        property_obj = Property.objects.create(name="The Painted Lady Inn")

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Already live at The Painted Lady Inn?")
        self.assertContains(response, reverse("existing_resident_intake", args=[property_obj.id]))

        property_obj.created_at = timezone.now() - timezone.timedelta(days=31)
        property_obj.save(update_fields=["created_at"])

        closed_response = self.client.get(reverse("home"))

        self.assertNotContains(closed_response, "Set Up My Profile")

    def test_admin_can_issue_property_owner_invite_from_intake(self):
        invite_admin = User.objects.create_superuser(
            username="invite-admin",
            email="invite-admin@example.com",
            password="StrongPass123!",
        )
        intake = PropertyOwnerIntake.objects.create(
            full_name="Invite Owner",
            email="invite-owner@example.com",
            phone="555-0193",
        )
        request = RequestFactory().post("/")
        request.user = invite_admin
        intake_admin = admin.site._registry[PropertyOwnerIntake]

        with patch.object(intake_admin, "message_user"):
            intake_admin.send_property_owner_portal_invites(
                request,
                PropertyOwnerIntake.objects.filter(id=intake.id),
            )

        intake.refresh_from_db()
        self.assertEqual(intake.status, "invited")
        self.assertIsNotNone(intake.user)
        self.assertTrue(intake.user.invite_code)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(intake.user.invite_code, mail.outbox[0].body)

    def test_staff_can_create_property_blog_and_approve_comment(self):
        staff_user = User.objects.create_user(
            username="staff-blog",
            email="staff-blog@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Blog Property")

        self.client.login(username="staff-blog", password="StrongPass123!")

        response = self.client.post(reverse("property_blog_create"), {
            "property": property_obj.id,
            "title": "Owner update",
            "body": "This is a property-specific update.",
        })

        self.assertRedirects(response, reverse("property_blog_manager"))
        post = BlogPost.objects.get(title="Owner update")
        self.assertEqual(post.property, property_obj)
        self.assertEqual(post.author, staff_user)

        comment = BlogComment.objects.create(
            post=post,
            name="Owner",
            email="owner@example.com",
            comment="Please approve this.",
            approved=False,
        )

        response = self.client.post(reverse("approve_blog_comment", args=[comment.id]))

        self.assertRedirects(response, reverse("property_blog_manager"))
        comment.refresh_from_db()
        self.assertTrue(comment.approved)

    def test_staff_can_delete_pending_blog_comment(self):
        staff_user = User.objects.create_user(
            username="staff-delete-comment",
            email="staff-delete-comment@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Comment Property")
        post = BlogPost.objects.create(
            property=property_obj,
            author=staff_user,
            title="Resident notice",
            body="Private property update.",
        )
        comment = BlogComment.objects.create(
            post=post,
            name="Bad Comment",
            email="bad-comment@example.com",
            comment="Do not approve.",
            approved=False,
        )

        self.client.login(username="staff-delete-comment", password="StrongPass123!")

        response = self.client.post(reverse("delete_blog_comment", args=[comment.id]))

        self.assertRedirects(response, reverse("property_blog_manager"))
        self.assertFalse(BlogComment.objects.filter(id=comment.id).exists())

    def test_homepage_only_shows_public_blog_posts(self):
        property_obj = Property.objects.create(name="Private Blog Property")
        BlogPost.objects.create(title="Public update", body="Public news.")
        BlogPost.objects.create(property=property_obj, title="Private resident update", body="Residents only.")

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public update")
        self.assertNotContains(response, "Private resident update")

    def test_property_blog_is_private_to_residents_of_that_property(self):
        property_obj = Property.objects.create(name="Resident Blog Property")
        BlogPost.objects.create(property=property_obj, title="Residents only notice", body="Private update.")

        anonymous_response = self.client.get(reverse("property_detail", args=[property_obj.id]))
        self.assertEqual(anonymous_response.status_code, 200)
        self.assertNotContains(anonymous_response, "Residents only notice")

        resident_user = User.objects.create_user(
            username="property-resident",
            email="property-resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        HousingApplication.objects.create(
            property=property_obj,
            user=resident_user,
            full_name="Property Resident",
            phone="555-0133",
            email="property-resident@example.com",
            age=45,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )

        self.client.login(username="property-resident", password="StrongPass123!")
        resident_response = self.client.get(reverse("property_detail", args=[property_obj.id]))

        self.assertEqual(resident_response.status_code, 200)
        self.assertContains(resident_response, "Residents only notice")

    def test_resident_property_blog_does_not_show_manager_link_or_other_property_updates(self):
        resident_property = Property.objects.create(name="Resident Property")
        other_property = Property.objects.create(name="Other Property")
        BlogPost.objects.create(property=resident_property, title="Resident update", body="Private notice.")
        BlogPost.objects.create(property=other_property, title="Other resident update", body="Do not show.")
        resident_user = User.objects.create_user(
            username="dashboard-blog-resident",
            email="dashboard-blog-resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        HousingApplication.objects.create(
            property=resident_property,
            user=resident_user,
            full_name="Dashboard Blog Resident",
            phone="555-0134",
            email="dashboard-blog-resident@example.com",
            age=46,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )

        self.client.login(username="dashboard-blog-resident", password="StrongPass123!")

        detail_response = self.client.get(reverse("property_detail", args=[resident_property.id]))
        dashboard_response = self.client.get(reverse("tenant_dashboard"))

        self.assertNotContains(detail_response, "Manage Blog")
        self.assertContains(dashboard_response, "Resident update")
        self.assertNotContains(dashboard_response, "Other resident update")

    def test_resident_balance_history_and_requests_pages_are_resident_scoped(self):
        resident_user = User.objects.create_user(
            username="balance-resident",
            email="balance-resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        application = HousingApplication.objects.create(
            user=resident_user,
            full_name="Balance Resident",
            phone="555-0135",
            email="balance-resident@example.com",
            age=44,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
            balance=Decimal("725.00"),
            utility_balance=Decimal("66.00"),
        )
        Payment.objects.create(
            application=application,
            payment_type="rent",
            amount=Decimal("725.00"),
            status="completed",
        )
        ResidentMessage.objects.create(
            application=application,
            message_type="maintenance",
            subject="Sink request",
            message="Check the sink.",
        )

        self.client.login(username="balance-resident", password="StrongPass123!")

        balance_response = self.client.get(reverse("resident_balance_detail"))
        history_response = self.client.get(reverse("resident_payment_history"))
        requests_response = self.client.get(reverse("resident_requests"))

        self.assertContains(balance_response, "Rent Due")
        self.assertContains(balance_response, "Pay Utilities")
        self.assertContains(history_response, "Payment History")
        self.assertContains(requests_response, "Sink request")

    def test_resident_upload_rejects_lease_document_type(self):
        resident_user = User.objects.create_user(
            username="document-upload-resident",
            email="document-upload-resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        HousingApplication.objects.create(
            user=resident_user,
            full_name="Document Upload Resident",
            phone="555-0136",
            email="document-upload-resident@example.com",
            age=43,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        document = SimpleUploadedFile("lease.pdf", b"not a signed lease", content_type="application/pdf")

        self.client.login(username="document-upload-resident", password="StrongPass123!")
        response = self.client.post(reverse("upload_resident_document"), {
            "document_type": "lease",
            "name": "Lease Upload",
            "file": document,
        })

        self.assertRedirects(response, reverse("tenant_dashboard"))
        self.assertFalse(ApplicantDocument.objects.filter(name="Lease Upload").exists())

    def test_staff_can_mark_uploaded_document_reviewed(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        application = HousingApplication.objects.create(
            full_name="Document Resident",
            phone="555-0106",
            email="document@example.com",
            age=47,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Needs review.",
        )
        document = ApplicantDocument.objects.create(
            application=application,
            document_type="id",
            name="Review Me",
            file="applicant_documents/review.pdf",
            status="uploaded",
            landlord_notified=False,
        )

        self.client.login(username="staff", password="StrongPass123!")

        response = self.client.post(reverse("mark_document_reviewed", args=[document.id]))

        self.assertRedirects(response, reverse("landlord_dashboard"))
        document.refresh_from_db()
        self.assertTrue(document.landlord_notified)

    def test_cleanup_test_portal_data_dry_run_deletes_nothing(self):
        application = HousingApplication.objects.create(
            full_name="Dry Run Resident",
            phone="555-0107",
            email="dryrun@example.com",
            age=48,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Test record.",
        )
        Payment.objects.create(
            application=application,
            payment_type="rent",
            payment_method="cash",
            amount=Decimal("1.00"),
            status="completed",
        )

        output = StringIO()
        call_command("cleanup_test_portal_data", stdout=output)

        self.assertIn("Dry run only", output.getvalue())
        self.assertEqual(HousingApplication.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

    def test_cleanup_test_portal_data_confirm_preserves_named_email_and_staff(self):
        staff_user = User.objects.create_user(
            username="owner",
            email="michael@bowlinglegacy.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        tenant_user = User.objects.create_user(
            username="test-tenant",
            email="tenant@example.com",
            role="tenant",
        )
        preserved_user = User.objects.create_user(
            username="preserved-tenant",
            email="keep@example.com",
            role="tenant",
        )
        test_application = HousingApplication.objects.create(
            full_name="Delete Me",
            phone="555-0108",
            email="tenant@example.com",
            age=49,
            user=tenant_user,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Test record.",
        )
        preserved_application = HousingApplication.objects.create(
            full_name="Keep Me",
            phone="555-0109",
            email="keep@example.com",
            age=50,
            user=preserved_user,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Real record.",
        )
        ResidentMessage.objects.create(
            application=test_application,
            subject="Delete message",
            message="Test",
        )
        ApplicantDocument.objects.create(
            application=test_application,
            document_type="id",
            name="Delete document",
            file="applicant_documents/delete.pdf",
        )
        Payment.objects.create(
            application=test_application,
            payment_type="rent",
            payment_method="cash",
            amount=Decimal("1.00"),
            status="completed",
        )

        output = StringIO()
        call_command(
            "cleanup_test_portal_data",
            "--confirm",
            "--preserve-email",
            "keep@example.com",
            stdout=output,
        )

        self.assertIn("Cleanup complete", output.getvalue())
        self.assertFalse(HousingApplication.objects.filter(id=test_application.id).exists())
        self.assertFalse(User.objects.filter(id=tenant_user.id).exists())
        self.assertTrue(HousingApplication.objects.filter(id=preserved_application.id).exists())
        self.assertTrue(User.objects.filter(id=preserved_user.id).exists())
        self.assertTrue(User.objects.filter(id=staff_user.id).exists())
        self.assertEqual(ResidentMessage.objects.count(), 0)
        self.assertEqual(ApplicantDocument.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)
