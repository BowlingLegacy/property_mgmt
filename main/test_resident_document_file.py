from django.contrib.admin.models import LogEntry
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import ApplicantDocument, HousingApplication, Property, SignedDocument, User


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class ResidentDocumentFileTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="document-landlord", password="test-password", email="landlord@example.com", role="landlord", is_staff=True)
        self.prop = Property.objects.create(name="Managed", landlord_email=self.staff.email)
        self.tenant = User.objects.create_user(username="document-resident", role="tenant")
        self.app = HousingApplication.objects.create(property=self.prop, user=self.tenant, full_name="Resident One", phone="5035550100", age=40, income_source="Work", monthly_income=2000, housing_need="Housing", space_label="N")
        self.url = reverse("resident_document_file", args=[self.app.pk])
        self.client.force_login(self.staff)

    def test_file_lists_onboarding_and_uploads_with_private_links(self):
        lease = SignedDocument.objects.create(application=self.app, document_type="lease", title="Signed resident lease", locked=True, signed_at=timezone.now(), resident_signature="Resident One", signed_lease_html="Preserved signed lease")
        emergency = SignedDocument.objects.create(application=self.app, document_type="emergency_contact", title="Emergency Contact Sheet")
        upload = ApplicantDocument.objects.create(application=self.app, name="Scanned onboarding packet", document_type="onboarding", file="applicant_documents/packet.pdf")
        response = self.client.get(self.url)
        self.assertContains(response, "Signed / Locked")
        self.assertContains(response, "Awaiting resident signature")
        self.assertContains(response, "Scanned onboarding packet")
        self.assertContains(response, reverse("open_applicant_document", args=[upload.pk]))
        for document in [lease, emergency]:
            doc_url = f'{reverse("onboarding_document", args=[document.pk])}?resident={self.app.pk}'
            self.assertContains(response, doc_url)
            self.assertEqual(self.client.get(doc_url).status_code, 200)
        lease.refresh_from_db()
        self.assertTrue(lease.locked)
        self.assertEqual(lease.resident_signature, "Resident One")
        self.assertEqual(lease.signed_lease_html, "Preserved signed lease")
        self.assertFalse(LogEntry.objects.exists())

    def test_empty_file_reports_missing_without_creating_documents(self):
        response = self.client.get(self.url)
        self.assertContains(response, "No document on file", count=3)
        self.assertContains(response, "No onboarding documents on file for this resident.")
        self.assertFalse(SignedDocument.objects.exists())

    def test_unrelated_resident_documents_are_excluded(self):
        other = HousingApplication.objects.create(property=self.prop, full_name="Other Resident", phone="5035550101", age=40, income_source="Work", monthly_income=2000, housing_need="Housing", space_label="O")
        SignedDocument.objects.create(application=other, title="PRIVATE OTHER RESIDENT")
        self.assertNotContains(self.client.get(self.url), "PRIVATE OTHER RESIDENT")

    def test_unmanaged_property_file_is_private(self):
        self.app.property = Property.objects.create(name="Unmanaged")
        self.app.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_signed_documents_on_earlier_file_remain_accessible(self):
        older = HousingApplication.objects.create(property=self.prop, full_name=self.app.full_name, phone="+15035550100", age=40, income_source="Work", monthly_income=2000, housing_need="Housing", space_label="M", tenancy_status="former")
        lease = SignedDocument.objects.create(application=older, document_type="lease", title="Original signed lease", locked=True, signed_at=timezone.now(), resident_signature="Resident One")
        response = self.client.get(self.url)
        self.assertContains(response, "Documents from Earlier Resident Files")
        self.assertContains(response, "Original signed lease")
        doc_url = f'{reverse("onboarding_document", args=[lease.pk])}?resident={older.pk}'
        self.assertContains(response, doc_url)
        self.assertEqual(self.client.get(doc_url).status_code, 200)
        lease.refresh_from_db()
        self.assertTrue(lease.locked)
        self.assertEqual(lease.application_id, older.pk)

    def test_historical_match_requires_name_and_contact_at_same_property(self):
        for prop, name, phone in [(self.prop, self.app.full_name, "5035550199"), (self.prop, "Different Resident", self.app.phone), (Property.objects.create(name="Other"), self.app.full_name, self.app.phone)]:
            older = HousingApplication.objects.create(property=prop, full_name=name, phone=phone, age=40, income_source="Work", monthly_income=2000, housing_need="Housing", tenancy_status="former")
            SignedDocument.objects.create(application=older, title="PRIVATE HISTORY")
        self.assertNotContains(self.client.get(self.url), "PRIVATE HISTORY")

    def test_tenant_and_anonymous_cannot_open_staff_file(self):
        self.client.force_login(self.tenant)
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_resident_lists_link_to_each_file(self):
        self.assertContains(self.client.get(reverse("landlord_resident_files")), self.url)
        self.staff.role = "admin"
        self.staff.save(update_fields=["role"])
        self.assertContains(self.client.get(reverse("superadmin_residents")), self.url)
