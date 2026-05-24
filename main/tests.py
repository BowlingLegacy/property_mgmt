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

from .models import AccountingReceipt, ApplicantDocument, BlogComment, BlogPost, CurrentResidentRosterEntry, ExistingResidentIntake, ExpenseCategory, FinancialEntry, FinancialUpload, HousingApplication, LandlordIntake, Payment, Property, PropertyOnboardingDocument, PropertyOwnerIntake, ResidentMessage, ResidentMessageReply, SignedDocument, User
from .views import apply_completed_payment_to_balance, ensure_existing_resident_portal_application


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

    def test_application_inherits_property_fee_and_background_requirements(self):
        property_obj = Property.objects.create(
            name="Fee Property",
            charges_application_fee=True,
            application_fee_amount=Decimal("35.00"),
            requires_background_check=True,
            background_check_fee_amount=Decimal("45.00"),
        )

        response = self.client.post(
            f"{reverse('apply')}?property={property_obj.id}",
            self.application_payload(),
        )

        self.assertEqual(response.status_code, 302)
        application = HousingApplication.objects.get(email="applicant@example.com")
        self.assertEqual(application.application_fee_amount, Decimal("35.00"))
        self.assertTrue(application.background_check_required)
        self.assertEqual(application.background_check_fee_amount, Decimal("45.00"))
        self.assertEqual(application.background_check_status, "pending")

    def test_application_fee_payment_updates_fee_balance(self):
        application = HousingApplication.objects.create(
            full_name="Fee Applicant",
            phone="555-0100",
            email="fee@example.com",
            age=42,
            application_fee_amount=Decimal("35.00"),
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Needs housing.",
        )
        payment = Payment.objects.create(
            application=application,
            payment_type="application_fee",
            payment_method="cash",
            amount=Decimal("35.00"),
            status="completed",
        )

        apply_completed_payment_to_balance(payment)

        application.refresh_from_db()
        self.assertEqual(application.application_fee_paid, Decimal("35.00"))

    @patch("main.views.stripe.checkout.Session.create")
    def test_recent_applicant_can_pay_application_fee_from_success_session(self, mock_session_create):
        mock_session_create.return_value = type("StripeSession", (), {
            "id": "cs_test_fee",
            "url": "https://checkout.stripe.test/session",
        })()
        property_obj = Property.objects.create(
            name="Fee Property",
            charges_application_fee=True,
            application_fee_amount=Decimal("35.00"),
        )

        self.client.post(
            f"{reverse('apply')}?property={property_obj.id}",
            self.application_payload(),
        )
        application = HousingApplication.objects.get(email="applicant@example.com")

        response = self.client.get(reverse("pay_by_type", args=[application.id, "application_fee"]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://checkout.stripe.test/session")
        payment = Payment.objects.get(application=application, payment_type="application_fee")
        self.assertEqual(payment.amount, Decimal("35.00"))

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
        property_obj = Property.objects.create(name="Invite Property", landlord_email=staff_user.email)
        application = HousingApplication.objects.create(
            property=property_obj,
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
        property_obj = Property.objects.create(name="Manual Transfer Property", landlord_email=staff_user.email)
        application = HousingApplication.objects.create(
            property=property_obj,
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
        property_obj = Property.objects.create(name="Cash App Property", landlord_email=staff_user.email)
        application = HousingApplication.objects.create(
            property=property_obj,
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
        property_obj = Property.objects.create(name="Attention Property", landlord_email=staff_user.email)
        application = HousingApplication.objects.create(
            property=property_obj,
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

    def test_landlord_can_reply_to_scoped_resident_message(self):
        landlord = User.objects.create_user(
            username="reply-landlord",
            email="reply-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Reply Property", landlord_email=landlord.email)
        application = HousingApplication.objects.create(
            property=property_obj,
            full_name="Reply Resident",
            phone="555-0106",
            email="reply-resident@example.com",
            age=46,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Needs review.",
        )
        resident_message = ResidentMessage.objects.create(
            application=application,
            message_type="maintenance",
            subject="Repair request",
            message="Please fix this.",
            status="submitted",
        )

        self.client.login(username="reply-landlord", password="StrongPass123!")
        response = self.client.post(reverse("landlord_message_detail", args=[resident_message.id]), {
            "reply_body": "I will check this today.",
        })

        self.assertRedirects(response, reverse("landlord_message_detail", args=[resident_message.id]))
        reply = ResidentMessageReply.objects.get(message=resident_message)
        self.assertEqual(reply.sender, landlord)
        self.assertEqual(reply.body, "I will check this today.")
        resident_message.refresh_from_db()
        self.assertEqual(resident_message.status, "reviewed")

    def test_landlord_cannot_reply_to_other_property_message(self):
        landlord = User.objects.create_user(
            username="blocked-reply-landlord",
            email="blocked-reply-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        other_property = Property.objects.create(name="Other Reply Property", landlord_email="other@example.com")
        application = HousingApplication.objects.create(
            property=other_property,
            full_name="Other Reply Resident",
            phone="555-0107",
            email="other-reply-resident@example.com",
            age=46,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Needs review.",
        )
        resident_message = ResidentMessage.objects.create(
            application=application,
            subject="Other request",
            message="Private message.",
        )

        self.client.login(username="blocked-reply-landlord", password="StrongPass123!")
        response = self.client.post(reverse("landlord_message_detail", args=[resident_message.id]), {
            "reply_body": "Should not send.",
        })

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ResidentMessageReply.objects.filter(message=resident_message).exists())

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

        dashboard_response = self.client.get(reverse("tenant_dashboard"))

        self.assertContains(dashboard_response, "Change Photo")

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
            phone="5550112233",
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
        self.assertContains(response, "(555) 011-2233")
        self.assertContains(response, "Renters Insurance")
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

    def test_property_owner_can_add_property_invite_landlord_and_upload_financial_file(self):
        owner = User.objects.create_user(
            username="workflow-owner",
            email="workflow-owner@example.com",
            password="StrongPass123!",
            role="property_owner",
        )
        self.client.login(username="workflow-owner", password="StrongPass123!")

        property_response = self.client.post(reverse("owner_property_create"), {
            "name": "Owner Added Property",
            "address": "100 Owner Way",
            "description": "Owner created property.",
            "rent_amount": "1450.00",
            "lease_type": "lease",
            "availability_status": "full",
            "availability_message": "Profile setup underway",
        })

        self.assertRedirects(
            property_response,
            reverse("owner_property_onboarding_documents", args=[Property.objects.get(name="Owner Added Property").id]),
        )
        property_obj = Property.objects.get(name="Owner Added Property")
        self.assertEqual(property_obj.owner_email, owner.email)
        self.assertEqual(property_obj.rent_amount, Decimal("1450.00"))
        self.assertEqual(property_obj.lease_type, "lease")

        onboarding_response = self.client.post(
            reverse("owner_property_onboarding_documents", args=[property_obj.id]),
            {
                "application_file": SimpleUploadedFile("rental-application.pdf", b"application", content_type="application/pdf"),
                "lease_file": SimpleUploadedFile("lease.pdf", b"lease", content_type="application/pdf"),
                "other_documents": SimpleUploadedFile("house-rules.pdf", b"rules", content_type="application/pdf"),
            },
        )

        self.assertRedirects(onboarding_response, reverse("property_owner_dashboard"))
        self.assertEqual(
            set(PropertyOnboardingDocument.objects.filter(property=property_obj).values_list("document_type", flat=True)),
            {"application", "lease", "other"},
        )

        landlord_response = self.client.post(reverse("owner_landlord_invite"), {
            "property": property_obj.id,
            "full_name": "Assigned Landlord",
            "email": "assigned-landlord@example.com",
            "phone": "555-0197",
            "address": "200 Manager Way",
        })

        self.assertRedirects(landlord_response, reverse("property_owner_dashboard"))
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.landlord_email, "assigned-landlord@example.com")
        intake = LandlordIntake.objects.get(email="assigned-landlord@example.com")
        self.assertEqual(intake.status, "invited")
        self.assertTrue(intake.user.invite_code)
        self.assertEqual(len(mail.outbox), 1)

        financial_file = SimpleUploadedFile("owner.csv", b"date,amount\n2026-05-01,100", content_type="text/csv")
        upload_response = self.client.post(reverse("owner_financial_upload"), {
            "property": property_obj.id,
            "name": "Owner Upload",
            "file": financial_file,
            "notes": "QuickBooks export",
        })

        self.assertRedirects(upload_response, reverse("owner_financial_upload"))
        self.assertEqual(property_obj.financial_uploads.get(name="Owner Upload").notes, "QuickBooks export")

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
            "charges_application_fee": "on",
            "performs_background_checks": "on",
            "advertises_available_units": "on",
            "uses_automatic_late_fees": "on",
            "needs_custom_reports": "on",
            "offers_renters_insurance": "on",
            "dashboard_goals": "Show NOI and rent collection by property.",
        })

        self.assertRedirects(response, reverse("property_owner_intake_success"))
        intake = PropertyOwnerIntake.objects.get(email="portfolio@example.com")
        self.assertEqual(intake.property_count, 4)
        self.assertEqual(intake.total_units, 120)
        self.assertEqual(intake.property_types, "multifamily,commercial")
        self.assertTrue(intake.needs_accounting)
        self.assertTrue(intake.needs_data_migration)
        self.assertTrue(intake.charges_application_fee)
        self.assertTrue(intake.performs_background_checks)
        self.assertTrue(intake.advertises_available_units)
        self.assertTrue(intake.uses_automatic_late_fees)
        self.assertTrue(intake.needs_custom_reports)
        self.assertTrue(intake.offers_renters_insurance)

    def test_existing_resident_intake_button_opens_for_new_property_and_saves_profile(self):
        property_obj = Property.objects.create(name="Painted Lady Inn")
        CurrentResidentRosterEntry.objects.create(
            property=property_obj,
            first_name="Existing",
            last_name="Resident",
            email="existing@example.com",
            phone="555-0195",
            room_unit_label="Room B",
        )

        property_response = self.client.get(reverse("property_detail", args=[property_obj.id]))
        self.assertEqual(property_response.status_code, 200)
        self.assertContains(property_response, "Existing Resident Profile")

        response = self.client.post(reverse("existing_resident_intake", args=[property_obj.id]), {
            "first_name": "Existing",
            "middle_name": "R",
            "last_name": "Resident",
            "email": "existing@example.com",
            "phone": "555-0195",
            "room_unit_label": "Room B",
            "has_valid_odl": "on",
            "years_at_residence": "3",
            "move_in_month": "2023-07",
        })

        self.assertRedirects(response, reverse("existing_resident_intake_success", args=[property_obj.id]))
        intake = ExistingResidentIntake.objects.get(email="existing@example.com")
        self.assertEqual(intake.property, property_obj)
        self.assertEqual(intake.full_name(), "Existing R Resident")
        self.assertEqual(intake.room_unit_label, "Room B")
        self.assertEqual(intake.move_in_month, "2023-07")
        self.assertTrue(intake.has_valid_odl)
        application = HousingApplication.objects.get(email="existing@example.com")
        self.assertEqual(application.property, property_obj)
        self.assertEqual(application.space_type, "Room")
        self.assertEqual(application.space_label, "Room B")
        self.assertIsNotNone(application.user)
        self.assertEqual(application.deposit_required, Decimal("0.00"))
        self.assertEqual(application.utility_monthly, Decimal("0.00"))
        self.assertIn(application.user.invite_code, mail.outbox[0].body)

    def test_existing_resident_intake_does_not_auto_invite_without_roster_match(self):
        property_obj = Property.objects.create(name="Roster Protected Property")
        CurrentResidentRosterEntry.objects.create(
            property=property_obj,
            first_name="Approved",
            last_name="Resident",
            email="approved@example.com",
            room_unit_label="Room A",
        )

        response = self.client.post(reverse("existing_resident_intake", args=[property_obj.id]), {
            "first_name": "Unknown",
            "last_name": "Resident",
            "email": "unknown@example.com",
            "phone": "555-0196",
            "room_unit_label": "Room Z",
            "years_at_residence": "1",
        })

        self.assertRedirects(response, reverse("existing_resident_intake_success", args=[property_obj.id]))
        self.assertTrue(ExistingResidentIntake.objects.filter(email="unknown@example.com").exists())
        self.assertFalse(HousingApplication.objects.filter(email="unknown@example.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_landlord_workspace_only_lists_assigned_property_records(self):
        landlord = User.objects.create_user(
            username="assigned-landlord",
            email="assigned@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        assigned_property = Property.objects.create(name="Assigned Property", landlord_email=landlord.email)
        other_property = Property.objects.create(name="Other Property", landlord_email="other@example.com")
        assigned_application = HousingApplication.objects.create(
            property=assigned_property,
            full_name="Assigned Resident",
            phone="555-0198",
            email="assigned-resident@example.com",
            age=51,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        other_application = HousingApplication.objects.create(
            property=other_property,
            full_name="Other Resident",
            phone="555-0199",
            email="other-resident@example.com",
            age=52,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        Payment.objects.create(application=assigned_application, amount=Decimal("100.00"), status="completed")
        Payment.objects.create(application=other_application, amount=Decimal("200.00"), status="completed")

        self.client.login(username="assigned-landlord", password="StrongPass123!")

        resident_files = self.client.get(reverse("landlord_resident_files"))
        payment_log = self.client.get(reverse("payment_log"))

        self.assertContains(resident_files, "Assigned Resident")
        self.assertNotContains(resident_files, "Other Resident")
        self.assertContains(payment_log, "Assigned Resident")
        self.assertNotContains(payment_log, "Other Resident")

    def test_landlord_dashboard_lists_current_month_rent_and_utility_exceptions(self):
        landlord = User.objects.create_user(
            username="collection-landlord",
            email="collection@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        assigned_property = Property.objects.create(name="Collection Property", landlord_email=landlord.email)
        other_property = Property.objects.create(name="Other Collection Property", landlord_email="other@example.com")
        paid_resident = HousingApplication.objects.create(
            property=assigned_property,
            full_name="Paid Resident",
            phone="555-0301",
            email="paid-collection@example.com",
            age=51,
            space_label="A",
            monthly_rent=Decimal("500.00"),
            utility_monthly=Decimal("66.00"),
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        missing_utility_resident = HousingApplication.objects.create(
            property=assigned_property,
            full_name="Missing Utility Resident",
            phone="555-0302",
            email="missing-utility@example.com",
            age=52,
            space_label="B",
            monthly_rent=Decimal("500.00"),
            utility_monthly=Decimal("66.00"),
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        other_resident = HousingApplication.objects.create(
            property=other_property,
            full_name="Other Missing Resident",
            phone="555-0303",
            email="other-missing@example.com",
            age=53,
            space_label="C",
            monthly_rent=Decimal("500.00"),
            utility_monthly=Decimal("66.00"),
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        Payment.objects.create(application=paid_resident, payment_type="rent", amount=Decimal("500.00"), status="completed")
        Payment.objects.create(application=paid_resident, payment_type="utility", amount=Decimal("66.00"), status="completed")
        Payment.objects.create(application=missing_utility_resident, payment_type="rent", amount=Decimal("500.00"), status="completed")

        self.client.login(username="collection-landlord", password="StrongPass123!")

        response = self.client.get(reverse("landlord_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monthly Collection Watch")
        self.assertContains(response, "Missing Utility Resident")
        self.assertContains(response, "Utilities")
        self.assertNotContains(response, "Paid Resident</td>")
        self.assertNotContains(response, "Other Missing Resident")

    def test_custom_phone_report_scopes_to_landlord_property(self):
        landlord = User.objects.create_user(
            username="report-landlord",
            email="report-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        assigned_property = Property.objects.create(name="Report Property", landlord_email=landlord.email)
        other_property = Property.objects.create(name="Other Report Property", landlord_email="other@example.com")
        HousingApplication.objects.create(
            property=assigned_property,
            full_name="Report Resident",
            phone="5550113344",
            email="report-resident@example.com",
            age=51,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        HousingApplication.objects.create(
            property=other_property,
            full_name="Hidden Resident",
            phone="5550113355",
            email="hidden-resident@example.com",
            age=52,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )

        self.client.login(username="report-landlord", password="StrongPass123!")

        response = self.client.get(reverse("custom_reports"), {
            "report_type": "resident_phone_list",
            "property_id": assigned_property.id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resident Phone List")
        self.assertContains(response, "Report Resident")
        self.assertContains(response, "(555) 011-3344")
        self.assertNotContains(response, "Hidden Resident")

    def test_custom_reports_scope_to_property_owner_and_block_residents(self):
        owner = User.objects.create_user(
            username="report-owner",
            email="owner-report@example.com",
            password="StrongPass123!",
            role="property_owner",
        )
        resident_user = User.objects.create_user(
            username="report-resident-user",
            email="report-resident-user@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        owned_property = Property.objects.create(name="Owner Report Property", owner_email=owner.email)
        other_property = Property.objects.create(name="Different Owner Property", owner_email="different@example.com")
        HousingApplication.objects.create(
            property=owned_property,
            full_name="Owned Property Resident",
            phone="5550114455",
            email="owned-resident@example.com",
            age=51,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        HousingApplication.objects.create(
            property=other_property,
            full_name="Different Owner Resident",
            phone="5550114466",
            email="different-owner-resident@example.com",
            age=52,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )

        self.client.login(username="report-owner", password="StrongPass123!")

        response = self.client.get(reverse("custom_reports"), {
            "report_type": "resident_phone_list",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Owned Property Resident")
        self.assertNotContains(response, "Different Owner Resident")

        self.client.logout()
        self.client.login(username="report-resident-user", password="StrongPass123!")

        response = self.client.get(reverse("custom_reports"), {
            "report_type": "resident_phone_list",
        })

        self.assertEqual(response.status_code, 302)

    def test_custom_financial_report_can_mix_expense_types_and_print(self):
        superuser = User.objects.create_user(
            username="report-admin",
            email="report-admin@example.com",
            password="StrongPass123!",
            role="admin",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Expense Report Property")
        upload = FinancialUpload.objects.create(
            name="May Accounting Export",
            file=SimpleUploadedFile("may.csv", b"category,amount\n", content_type="text/csv"),
        )
        FinancialEntry.objects.create(
            upload=upload,
            property_name=property_obj.name,
            sheet_name="Expenses",
            row_number=1,
            year=2026,
            month=5,
            entry_type="operating_expense",
            category="Repairs",
            description="Plumbing repair",
            amount=Decimal("125.00"),
        )
        FinancialEntry.objects.create(
            upload=upload,
            property_name=property_obj.name,
            sheet_name="Expenses",
            row_number=2,
            year=2026,
            month=5,
            entry_type="capital_expense",
            category="Improvements",
            description="Floor replacement",
            amount=Decimal("400.00"),
        )
        FinancialEntry.objects.create(
            upload=upload,
            property_name=property_obj.name,
            sheet_name="Income",
            row_number=3,
            year=2026,
            month=5,
            entry_type="income",
            category="Rent",
            description="May rent",
            amount=Decimal("900.00"),
        )

        self.client.login(username="report-admin", password="StrongPass123!")

        response = self.client.get(reverse("custom_reports"), {
            "report_type": "financial_entries",
            "property_id": property_obj.id,
            "financial_entry_types": ["operating_expense", "capital_expense"],
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Financial Entries / Expenses")
        self.assertContains(response, "Plumbing repair")
        self.assertContains(response, "Floor replacement")
        self.assertContains(response, "$525.00")
        self.assertNotContains(response, "May rent")

    def test_accounting_receipt_upload_creates_category_and_review_record(self):
        landlord = User.objects.create_user(
            username="receipt-landlord",
            email="receipt-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Receipt Property", landlord_email=landlord.email)
        receipt_file = SimpleUploadedFile("receipt.pdf", b"%PDF-1.4 receipt", content_type="application/pdf")

        self.client.login(username="receipt-landlord", password="StrongPass123!")

        response = self.client.post(reverse("accounting_receipts"), {
            "property": property_obj.id,
            "receipt_file": receipt_file,
            "vendor": "Plumbing Vendor",
            "receipt_date": "2026-05-20",
            "entry_type": "operating_expense",
            "new_category": "Plumbing Repairs",
            "description": "Kitchen sink repair",
            "amount": "125.50",
            "payment_method": "check",
            "notes": "Uploaded from paper receipt.",
        })

        self.assertRedirects(response, reverse("accounting_receipts"))
        receipt = AccountingReceipt.objects.get(vendor="Plumbing Vendor")
        self.assertEqual(receipt.property, property_obj)
        self.assertEqual(receipt.status, "needs_review")
        self.assertEqual(receipt.category.name, "Plumbing Repairs")
        self.assertTrue(receipt.receipt_file.name)

    def test_accounting_receipt_approval_creates_financial_entry_and_scopes_property(self):
        landlord = User.objects.create_user(
            username="approve-receipt-landlord",
            email="approve-receipt-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Approval Property", landlord_email=landlord.email)
        other_property = Property.objects.create(name="Other Approval Property", landlord_email="other@example.com")
        category = ExpenseCategory.objects.create(name="Repairs", entry_type="operating_expense")
        receipt = AccountingReceipt.objects.create(
            property=property_obj,
            receipt_file="accounting_receipts/repair.pdf",
            vendor="Repair Vendor",
            receipt_date=timezone.datetime(2026, 5, 20).date(),
            category=category,
            entry_type="operating_expense",
            description="Door repair",
            amount=Decimal("225.00"),
            payment_method="cash",
        )
        other_receipt = AccountingReceipt.objects.create(
            property=other_property,
            receipt_file="accounting_receipts/other.pdf",
            vendor="Other Vendor",
            category=category,
            amount=Decimal("99.00"),
        )

        self.client.login(username="approve-receipt-landlord", password="StrongPass123!")

        blocked_response = self.client.post(reverse("approve_accounting_receipt", args=[other_receipt.id]))
        self.assertEqual(blocked_response.status_code, 404)

        response = self.client.post(reverse("approve_accounting_receipt", args=[receipt.id]))

        self.assertRedirects(response, reverse("accounting_receipts"))
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, "approved")
        self.assertIsNotNone(receipt.financial_entry)
        self.assertEqual(receipt.financial_entry.property_name, property_obj.name)
        self.assertEqual(receipt.financial_entry.category, "Repairs")
        self.assertEqual(receipt.financial_entry.amount, Decimal("225.00"))

    def test_accounting_import_maps_csv_to_property_scoped_ledger_entries(self):
        landlord = User.objects.create_user(
            username="accounting-landlord",
            email="accounting-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Accounting Property", landlord_email=landlord.email)
        csv_file = SimpleUploadedFile(
            "expenses.csv",
            b"Date,Vendor,Amount,Category\n2026-05-01,Power Company,-125.50,Utilities\n2026-05-03,Roof Vendor,-900.00,Capital Roof\n",
            content_type="text/csv",
        )

        self.client.login(username="accounting-landlord", password="StrongPass123!")
        upload_response = self.client.post(reverse("financial_upload"), {
            "property": property_obj.id,
            "name": "May Expenses",
            "file": csv_file,
            "notes": "Bank export",
        })

        upload = FinancialUpload.objects.get(name="May Expenses")
        self.assertRedirects(upload_response, reverse("parse_financial_upload", args=[upload.id]))

        response = self.client.post(reverse("parse_financial_upload", args=[upload.id]), {
            "date_column": "Date",
            "description_column": "Vendor",
            "amount_column": "Amount",
            "category_column": "Category",
            "entry_type_column": "",
            "property_column": "",
            "default_entry_type": "operating_expense",
            "default_category": "",
        })

        self.assertRedirects(response, reverse("parse_financial_upload", args=[upload.id]))
        entries = FinancialEntry.objects.filter(upload=upload).order_by("row_number")
        self.assertEqual(entries.count(), 2)
        self.assertEqual(entries[0].property_name, property_obj.name)
        self.assertEqual(entries[0].entry_date.isoformat(), "2026-05-01")
        self.assertEqual(entries[0].amount, Decimal("125.50"))
        self.assertEqual(entries[0].category, "Utilities")
        self.assertEqual(entries[1].entry_type, "capital_expense")
        self.assertTrue(ExpenseCategory.objects.filter(name="Utilities").exists())

    def test_accounting_import_blocks_other_landlord_property(self):
        landlord = User.objects.create_user(
            username="blocked-accounting-landlord",
            email="blocked-accounting-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        other_property = Property.objects.create(name="Other Accounting Property", landlord_email="other@example.com")
        csv_file = SimpleUploadedFile(
            "blocked.csv",
            b"Date,Vendor,Amount\n2026-05-01,Vendor,-10.00\n",
            content_type="text/csv",
        )

        self.client.login(username="blocked-accounting-landlord", password="StrongPass123!")
        response = self.client.post(reverse("financial_upload"), {
            "property": other_property.id,
            "name": "Blocked Upload",
            "file": csv_file,
            "notes": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(FinancialUpload.objects.filter(name="Blocked Upload").exists())

    def test_landlord_can_send_setup_invite_for_saved_current_resident_intake(self):
        landlord = User.objects.create_user(
            username="resident-intake-landlord",
            email="resident-intake-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Intake Property", landlord_email=landlord.email)
        intake = ExistingResidentIntake.objects.create(
            property=property_obj,
            first_name="Saved",
            last_name="Resident",
            email="saved-resident@example.com",
            phone="555-0200",
            room_unit_label="Unit 4",
        )

        self.client.login(username="resident-intake-landlord", password="StrongPass123!")

        response = self.client.post(reverse("landlord_send_existing_resident_invite", args=[intake.id]))

        self.assertRedirects(response, reverse("landlord_attention"))
        application = HousingApplication.objects.get(email="saved-resident@example.com")
        self.assertEqual(application.property, property_obj)
        self.assertEqual(application.space_label, "Unit 4")
        self.assertIn(application.user.invite_code, mail.outbox[0].body)

    def test_landlord_can_upload_current_resident_roster(self):
        landlord = User.objects.create_user(
            username="roster-landlord",
            email="roster-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Roster Property", landlord_email=landlord.email)
        roster_file = SimpleUploadedFile(
            "roster.csv",
            b"first_name,last_name,email,phone,room_unit_label\nRoster,Resident,roster@example.com,555-0300,Unit 12\n",
            content_type="text/csv",
        )

        self.client.login(username="roster-landlord", password="StrongPass123!")
        response = self.client.post(reverse("current_resident_roster_upload"), {
            "property": property_obj.id,
            "file": roster_file,
        })

        self.assertRedirects(response, reverse("current_resident_roster_upload"))
        roster_entry = CurrentResidentRosterEntry.objects.get(email="roster@example.com")
        self.assertEqual(roster_entry.property, property_obj)
        self.assertEqual(roster_entry.room_unit_label, "Unit 12")

    def test_landlord_can_view_current_resident_intake_detail_and_backup_code(self):
        landlord = User.objects.create_user(
            username="resident-intake-detail-landlord",
            email="resident-intake-detail-landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        property_obj = Property.objects.create(name="Intake Detail Property", landlord_email=landlord.email)
        intake = ExistingResidentIntake.objects.create(
            property=property_obj,
            first_name="Detail",
            last_name="Resident",
            email="detail-resident@example.com",
            phone="555-0201",
            room_unit_label="Unit 8",
        )
        application = ensure_existing_resident_portal_application(intake)
        application.user.refresh_invite_code()

        self.client.login(username="resident-intake-detail-landlord", password="StrongPass123!")
        response = self.client.get(reverse("landlord_existing_resident_intake_detail", args=[intake.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Resident")
        self.assertContains(response, "Unit 8")
        self.assertContains(response, application.user.invite_code)

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

    def test_superadmin_owner_intake_inbox_can_open_file_and_send_invite(self):
        User.objects.create_superuser(
            username="owner-intake-admin",
            email="owner-intake-admin@example.com",
            password="StrongPass123!",
            role="admin",
        )
        intake = PropertyOwnerIntake.objects.create(
            full_name="Owner Inbox User",
            company_name="Owner Inbox LLC",
            email="owner-inbox@example.com",
            phone="555-0196",
            dashboard_goals="Need reports by property.",
            needs_owner_reporting=True,
        )

        self.client.login(username="owner-intake-admin", password="StrongPass123!")

        inbox_response = self.client.get(reverse("superadmin_owner_intakes"))
        detail_response = self.client.get(reverse("superadmin_owner_intake_detail", args=[intake.id]))
        invite_response = self.client.post(reverse("superadmin_send_owner_invite", args=[intake.id]))

        self.assertContains(inbox_response, "Owner Inbox User")
        self.assertContains(detail_response, "Need reports by property.")
        self.assertRedirects(invite_response, reverse("superadmin_owner_intake_detail", args=[intake.id]))
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
        property_obj = Property.objects.create(name="Blog Property", landlord_email="staff-blog@example.com")

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
        property_obj = Property.objects.create(name="Comment Property", landlord_email="staff-delete-comment@example.com")
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

    def test_owner_and_landlord_blog_forms_only_offer_assigned_properties(self):
        owner_property = Property.objects.create(name="Owner Property", owner_email="owner-blog@example.com")
        landlord_property = Property.objects.create(name="Landlord Property", landlord_email="landlord-blog@example.com")
        Property.objects.create(name="Other Property", owner_email="other@example.com", landlord_email="other@example.com")
        BlogPost.objects.create(title="Public website note", body="Superuser only.")

        User.objects.create_user(
            username="owner-blog",
            email="owner-blog@example.com",
            password="StrongPass123!",
            role="property_owner",
        )
        User.objects.create_user(
            username="landlord-blog",
            email="landlord-blog@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )

        self.client.login(username="owner-blog", password="StrongPass123!")
        owner_form = self.client.get(reverse("property_blog_create"))
        owner_manager = self.client.get(reverse("property_blog_manager"))
        self.assertContains(owner_form, owner_property.name)
        self.assertNotContains(owner_form, landlord_property.name)
        self.assertNotContains(owner_manager, "Public website note")

        self.client.logout()
        self.client.login(username="landlord-blog", password="StrongPass123!")
        landlord_form = self.client.get(reverse("property_blog_create"))
        landlord_manager = self.client.get(reverse("property_blog_manager"))
        self.assertContains(landlord_form, landlord_property.name)
        self.assertNotContains(landlord_form, owner_property.name)
        self.assertNotContains(landlord_manager, "Public website note")

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

    def test_resident_can_reply_only_to_own_message(self):
        resident_user = User.objects.create_user(
            username="reply-resident",
            email="reply-resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        other_user = User.objects.create_user(
            username="other-reply-resident",
            email="other-reply-resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        application = HousingApplication.objects.create(
            user=resident_user,
            full_name="Reply Resident",
            phone="555-0137",
            email="reply-resident@example.com",
            age=43,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        other_application = HousingApplication.objects.create(
            user=other_user,
            full_name="Other Reply Resident",
            phone="555-0138",
            email="other-reply-resident@example.com",
            age=43,
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        resident_message = ResidentMessage.objects.create(
            application=application,
            subject="My request",
            message="My private request.",
        )
        other_message = ResidentMessage.objects.create(
            application=other_application,
            subject="Other request",
            message="Other private request.",
        )

        self.client.login(username="reply-resident", password="StrongPass123!")
        response = self.client.post(reverse("resident_requests"), {
            "message_id": resident_message.id,
            "reply_body": "Here is my reply.",
        })

        self.assertRedirects(response, reverse("resident_requests"))
        self.assertTrue(ResidentMessageReply.objects.filter(message=resident_message, body="Here is my reply.").exists())

        blocked_response = self.client.post(reverse("resident_requests"), {
            "message_id": other_message.id,
            "reply_body": "Trying to reply.",
        })
        self.assertEqual(blocked_response.status_code, 404)
        self.assertFalse(ResidentMessageReply.objects.filter(message=other_message).exists())

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
        property_obj = Property.objects.create(name="Document Property", landlord_email=staff_user.email)
        application = HousingApplication.objects.create(
            property=property_obj,
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
        superuser = User.objects.create_superuser(
            username="system-owner",
            email="superowner@example.com",
            password="StrongPass123!",
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
        self.assertTrue(User.objects.filter(id=superuser.id).exists())
        self.assertEqual(ResidentMessage.objects.count(), 0)
        self.assertEqual(ApplicantDocument.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

    def test_cleanup_preserves_felicia_name_and_only_completed_one_dollar_payment(self):
        felicia = HousingApplication.objects.create(
            full_name="Felicia Valdez",
            phone="555-0110",
            email="felicia@example.com",
            age=51,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Real application.",
        )
        felicia_document = SignedDocument.objects.create(
            application=felicia,
            document_type="lease",
            title="Felicia Lease Agreement",
            locked=True,
        )
        paid_application = HousingApplication.objects.create(
            full_name="Real Payment Resident",
            phone="555-0111",
            email="paid@example.com",
            age=52,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Real payment.",
        )
        test_application = HousingApplication.objects.create(
            full_name="Delete Test",
            phone="555-0112",
            email="delete@example.com",
            age=53,
            income_source="Employment",
            monthly_income=Decimal("3000.00"),
            housing_need="Delete me.",
        )
        kept_payment = Payment.objects.create(
            application=paid_application,
            payment_type="rent",
            payment_method="stripe_card",
            amount=Decimal("1.00"),
            status="completed",
        )
        Payment.objects.create(
            application=test_application,
            payment_type="rent",
            payment_method="cash",
            amount=Decimal("20.00"),
            status="completed",
        )

        output = StringIO()
        call_command(
            "cleanup_test_portal_data",
            "--confirm",
            "--preserve-only-completed-one-dollar-payment",
            "--keep-users",
            stdout=output,
        )

        self.assertTrue(HousingApplication.objects.filter(id=felicia.id).exists())
        self.assertTrue(SignedDocument.objects.filter(id=felicia_document.id).exists())
        self.assertTrue(HousingApplication.objects.filter(id=paid_application.id).exists())
        self.assertFalse(HousingApplication.objects.filter(id=test_application.id).exists())
        self.assertTrue(Payment.objects.filter(id=kept_payment.id).exists())

    def test_cleanup_deletes_only_explicitly_named_test_properties(self):
        abc_property = Property.objects.create(name="ABC CO PROPERTY")
        newtest_property = Property.objects.create(name="newtest fake property")
        real_property = Property.objects.create(name="Painted Lady Inn")

        preview = StringIO()
        call_command(
            "cleanup_test_portal_data",
            "--delete-property-name",
            "ABC CO PROPERTY",
            "--delete-property-name",
            "newtest fake property",
            stdout=preview,
        )

        self.assertIn("Properties selected by exact name: 2", preview.getvalue())
        self.assertTrue(Property.objects.filter(id=abc_property.id).exists())
        self.assertTrue(Property.objects.filter(id=newtest_property.id).exists())

        call_command(
            "cleanup_test_portal_data",
            "--confirm",
            "--delete-property-name",
            "ABC CO PROPERTY",
            "--delete-property-name",
            "newtest fake property",
        )

        self.assertFalse(Property.objects.filter(id=abc_property.id).exists())
        self.assertFalse(Property.objects.filter(id=newtest_property.id).exists())
        self.assertTrue(Property.objects.filter(id=real_property.id).exists())
