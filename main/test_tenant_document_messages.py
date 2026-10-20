from datetime import date, datetime
from io import BytesIO
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from reportlab.pdfgen import canvas
from .models import (
    User,
    Property,
    HousingApplication,
    ResidentMessage,
    ResidentLateFeePolicy,
    ResidentBalanceEntry,
    Payment,
)
from .late_fees import assess_late_fees

PT = ZoneInfo("America/Los_Angeles")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", SMS_PROVIDER=""
)
class TenantDocumentTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.owner = User.objects.create_user(
            username="form-owner",
            password="test-pass",
            email="owner@example.com",
            role="landlord",
            is_staff=True,
        )
        self.user = User.objects.create_user(username="form-tenant", role="tenant")
        self.prop = Property.objects.create(
            name="The Painted Lady Inn", landlord_email=self.owner.email
        )
        self.app = HousingApplication.objects.create(
            user=self.user,
            property=self.prop,
            full_name="Test Tenant",
            age=40,
            phone="5555550100",
            income_source="Work",
            monthly_income=2000,
            housing_need="Housing",
            monthly_rent=650,
            lease_start_date=date(2026, 9, 1),
        )
        self.client.force_login(self.user)

    def pdf(self):
        b = BytesIO()
        c = canvas.Canvas(b)
        c.drawString(50, 700, "Tenant notice")
        c.save()
        return SimpleUploadedFile("notice.pdf", b.getvalue(), "application/pdf")

    def submit(self, **kwargs):
        data = dict(
            message_type="move_out",
            subject="Move-out notice",
            message="Please review my notice.",
            attachment=self.pdf(),
        )
        data.update(kwargs)
        return self.client.post(reverse("submit_resident_message"), data)

    def test_pdf_filed_in_inbox_and_access_is_private(self):
        self.submit()
        msg = ResidentMessage.objects.get()
        self.assertTrue(msg.attachment.locked)
        self.assertEqual(msg.attachment.application, self.app)
        url = reverse("open_applicant_document", args=[msg.attachment_id])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(
            self.client.get(reverse("resident_requests")), "View your submitted PDF"
        )
        self.client.force_login(self.owner)
        self.assertContains(
            self.client.get(reverse("landlord_message_detail", args=[msg.pk])),
            "Open submitted PDF form",
        )
        self.assertEqual(self.client.get(url).status_code, 200)
        stranger = User.objects.create_user(username="stranger", role="tenant")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.get(reverse("tenant_form", args=["move_out"])).status_code, 404
        )
        outsider = User.objects.create_user(
            username="outsider",
            password="test-pass",
            role="landlord",
            is_staff=True,
            email="other@example.com",
        )
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.get(
                reverse("landlord_message_detail", args=[msg.pk])
            ).status_code,
            404,
        )

    def test_missing_fake_or_invalid_type_rejected(self):
        self.submit(attachment="")
        self.submit(
            attachment=SimpleUploadedFile("fake.pdf", b"not a pdf", "application/pdf")
        )
        self.submit(message_type="invented")
        self.assertFalse(ResidentMessage.objects.exists())

    def test_ordinary_message_still_works_without_pdf(self):
        self.submit(message_type="general", attachment="")
        self.assertIsNone(ResidentMessage.objects.get().attachment)

    def request_arrangement(self):
        msg = ResidentMessage.objects.create(
            application=self.app,
            message_type="late_payment",
            subject="Late rent",
            message="Pay on 10th",
            service_month=date(2026, 10, 1),
            promised_payment_date=date(2026, 10, 10),
        )
        ResidentLateFeePolicy.objects.create(
            application=self.app,
            enabled=True,
            amount=25,
            grace_days=4,
            effective_from=date(2026, 10, 1),
            confirmed_at=datetime(2026, 10, 1, tzinfo=PT),
        )
        return msg

    def approve(self, msg):
        self.client.force_login(self.owner)
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 10, 4, 12, tzinfo=PT),
        ):
            return self.client.post(
                reverse("landlord_message_detail", args=[msg.pk]),
                dict(
                    approve_arrangement="yes",
                    reply_body="Approved; please pay on time.",
                ),
            )

    def test_pending_request_does_not_pause_fee(self):
        self.request_arrangement()
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 1)

    def test_approved_request_defers_until_day_after_promise(self):
        msg = self.request_arrangement()
        self.approve(msg)
        msg.refresh_from_db()
        self.assertEqual(msg.arrangement_approved_by, self.owner)
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 10))["assessed"], 0)
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 11))["assessed"], 1)
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 11))["assessed"], 0)

    def test_payment_by_approved_deadline_avoids_fee(self):
        msg = self.request_arrangement()
        self.approve(msg)
        Payment.objects.create(
            application=self.app,
            payment_type="rent",
            amount=650,
            status="completed",
            service_month=date(2026, 10, 1),
            received_at=datetime(2026, 10, 10, 23, 59, tzinfo=PT),
        )
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 11))["assessed"], 0)

    def test_existing_fee_cannot_be_erased_by_approval(self):
        msg = self.request_arrangement()
        assess_late_fees(as_of=date(2026, 10, 6))
        self.approve(msg)
        msg.refresh_from_db()
        self.assertIsNone(msg.arrangement_approved_at)
        self.assertEqual(
            ResidentBalanceEntry.objects.filter(balance_type="late_fee").count(), 1
        )

    def test_tenant_cannot_self_approve(self):
        msg = self.request_arrangement()
        self.client.post(
            reverse("landlord_message_detail", args=[msg.pk]),
            dict(approve_arrangement="yes", reply_body="approved"),
        )
        msg.refresh_from_db()
        self.assertIsNone(msg.arrangement_approved_at)

    def test_all_form_downloads_and_dashboard_links(self):
        from .resident_forms import FORM_TYPES

        response = self.client.get(reverse("tenant_dashboard"))
        self.assertContains(response, "Cash App $Trmf8763")
        for kind in FORM_TYPES:
            url = reverse("tenant_form", args=[kind])
            self.assertContains(response, url)
            download = self.client.get(url)
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download["Content-Type"], "application/pdf")

    def test_previous_signed_lease_keeps_previous_terms(self):
        from .models import SignedDocument

        lease = SignedDocument.objects.create(
            application=self.app,
            document_type="lease",
            title="Prior signed lease",
            locked=True,
            lease_version="painted-lady-2026-10-19",
            signed_at=timezone.now(),
            signed_lease_html="<p>Accepted October 19 terms</p>",
        )
        response = self.client.get(reverse("onboarding_document", args=[lease.pk]))
        self.assertContains(response, "Accepted October 19 terms")
        self.assertNotContains(response, "Only written landlord approval")
        self.assertTemplateUsed(response, "lease_sign.html")

    def test_long_arrangement_is_not_lost_after_two_months(self):
        msg = self.request_arrangement()
        msg.promised_payment_date = date(2026, 12, 10)
        msg.save()
        self.approve(msg)
        assess_late_fees(as_of=date(2026, 12, 11))
        self.assertTrue(
            ResidentBalanceEntry.objects.filter(
                balance_type="late_fee", service_month=date(2026, 10, 1)
            ).exists()
        )

    def test_generated_forms_can_be_submitted(self):
        from pathlib import Path
        from django.conf import settings
        from .resident_forms import FORM_TYPES

        for kind in FORM_TYPES:
            content = (
                Path(settings.BASE_DIR) / "static/forms" / ("tenant_" + kind + ".pdf")
            ).read_bytes()
            response = self.submit(
                message_type=kind,
                attachment=SimpleUploadedFile("form.pdf", content, "application/pdf"),
                service_month="2026-10",
                promised_payment_date="2099-10-10",
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(
                ResidentMessage.objects.filter(
                    message_type=kind, attachment__isnull=False
                ).exists(),
                kind,
            )
