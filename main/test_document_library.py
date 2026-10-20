from pathlib import Path
from tempfile import TemporaryDirectory
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import (
    User,
    Property,
    HousingApplication,
    ResidentMessage,
    Payment,
    ResidentBalanceEntry,
)
from .document_library import DOCUMENTS


class DocumentLibraryTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.owner = User.objects.create_user(
            username="library-owner",
            email="library@example.com",
            password="test-pass",
            role="landlord",
            is_staff=True,
        )
        self.tenant = User.objects.create_user(username="library-tenant", role="tenant")
        self.property = Property.objects.create(
            name="Belmont", landlord_email=self.owner.email
        )
        self.resident = HousingApplication.objects.create(
            user=self.tenant,
            property=self.property,
            full_name="Library Resident",
            age=30,
            phone="5555551234",
            income_source="Work",
            monthly_income=2000,
            housing_need="Housing",
        )

    def test_library_and_originals_are_private(self):
        url = reverse("document_library")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.tenant)
        self.assertEqual(self.client.get(url).status_code, 403)
        for key in DOCUMENTS:
            self.assertEqual(
                self.client.get(reverse("library_download", args=[key])).status_code,
                403,
            )
        self.assertEqual(
            self.client.get(
                "/private_forms/originals/receipt_original.pdf"
            ).status_code,
            404,
        )

    def test_staff_can_download_all_preserved_originals_and_fillable_forms(self):
        self.client.force_login(self.owner)
        self.assertContains(
            self.client.get(reverse("document_library")), "Needs review before use"
        )
        for key, entry in DOCUMENTS.items():
            response = self.client.get(reverse("library_download", args=[key]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                b"".join(response.streaming_content),
                (
                    Path(settings.BASE_DIR) / "private_forms" / entry["file"]
                ).read_bytes(),
            )

    def upload(self, **changes):
        data = dict(
            resident=self.resident.pk,
            document_kind="receipt",
            attachment=SimpleUploadedFile(
                "receipt.pdf",
                (
                    Path(settings.BASE_DIR) / "private_forms/rent_receipt_fillable.pdf"
                ).read_bytes(),
                "application/pdf",
            ),
        )
        data.update(changes)
        return self.client.post(reverse("document_library"), data)

    def test_file_receipt_in_resident_inbox_without_posting_money(self):
        self.client.force_login(self.owner)
        response = self.upload()
        self.assertRedirects(response, reverse("document_library"))
        msg = ResidentMessage.objects.get()
        self.assertEqual(msg.application, self.resident)
        self.assertTrue(msg.attachment.locked)
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(ResidentBalanceEntry.objects.exists())
        self.client.force_login(self.tenant)
        self.assertContains(
            self.client.get(reverse("resident_requests")), "Fillable rent receipt"
        )
        response = self.client.get(reverse("open_applicant_document", args=[msg.attachment_id]))
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_cannot_file_for_other_landlords_resident(self):
        other = User.objects.create_user(
            username="library-other",
            email="other@example.com",
            password="test-pass",
            role="landlord",
            is_staff=True,
        )
        self.client.force_login(other)
        self.assertEqual(self.upload().status_code, 404)
        self.assertFalse(ResidentMessage.objects.exists())

    def test_reference_notice_cannot_be_filed_as_usable_form(self):
        self.client.force_login(self.owner)
        self.upload(document_kind="violation_one")
        self.assertFalse(ResidentMessage.objects.exists())

    def test_missing_or_fake_pdf_rejected(self):
        self.client.force_login(self.owner)
        self.upload(attachment="")
        self.upload(
            attachment=SimpleUploadedFile("fake.pdf", b"fake pdf", "application/pdf")
        )
        self.assertFalse(ResidentMessage.objects.exists())

    def test_invalid_resident_and_unknown_file_return_not_found(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.upload(resident="bad").status_code, 404)
        self.assertEqual(
            self.client.get(reverse("library_download", args=["unknown"])).status_code,
            404,
        )
