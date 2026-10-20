from django.contrib.admin.models import LogEntry
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import HousingApplication, Property, User
from .views import resident_can_receive_sms


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class ResidentContactTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="contact-landlord", email="landlord@example.com", password="test-password", role="landlord", is_staff=True)
        self.tenant = User.objects.create_user(username="contact-tenant", role="tenant")
        self.prop = Property.objects.create(name="Managed", landlord_email=self.staff.email)
        self.app = HousingApplication.objects.create(property=self.prop, user=self.tenant, full_name="Aaron Brown", phone="+15035550100", age=40, income_source="Work", monthly_income=2000, housing_need="Housing", space_label="N")
        self.url = reverse("edit_resident_contact", args=[self.app.pk])
        self.client.force_login(self.staff)

    def data(self, **extra):
        return dict(phone="503-555-0101", email="aaron@example.com", sms_action="keep", **extra)

    def test_landlord_has_dashboard_and_contact_links(self):
        response = self.client.get(reverse("landlord_resident_files"))
        self.assertContains(response, f'{reverse("tenant_dashboard")}?resident={self.app.pk}')
        self.assertContains(response, self.url)
        dashboard = self.client.get(f'{reverse("tenant_dashboard")}?resident={self.app.pk}')
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, self.url)

    def test_verbal_consent_saved_with_actor_and_details(self):
        data = self.data()
        data.update(sms_action="consent", consent_notes="Resident verbally consented to maintenance SMS on October 20, 2026.")
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.app.refresh_from_db()
        self.assertEqual(self.app.phone, "+15035550101")
        self.assertTrue(resident_can_receive_sms(self.app))
        self.assertIsNotNone(self.app.sms_opted_in_at)
        self.assertEqual(self.app.communication_preference, "sms")
        self.assertFalse(self.app.sms_phone_verified)
        log = LogEntry.objects.get()
        self.assertEqual(log.user_id, self.staff.pk)
        self.assertIn(data["consent_notes"], log.change_message)
        self.assertEqual(log.object_id, str(self.app.pk))

    def test_consent_requires_details(self):
        data = self.data()
        data["sms_action"] = "consent"
        response = self.client.post(self.url, data)
        self.assertContains(response, "Record how and when")
        self.app.refresh_from_db()
        self.assertEqual(self.app.phone, "+15035550100")
        self.assertFalse(self.app.sms_opted_in)
        self.assertFalse(LogEntry.objects.exists())

    def test_number_change_does_not_transfer_consent(self):
        self.app.sms_opted_in = True
        self.app.sms_opted_in_at = timezone.now()
        self.app.sms_phone_verified = True
        self.app.communication_preference = "sms"
        self.app.save()
        self.client.post(self.url, self.data())
        self.app.refresh_from_db()
        self.assertFalse(resident_can_receive_sms(self.app))
        self.assertFalse(self.app.sms_phone_verified)
        self.assertIsNone(self.app.sms_opted_in_at)
        self.assertEqual(self.app.communication_preference, "portal")

    def test_format_change_preserves_consent(self):
        self.app.sms_opted_in = True
        self.app.sms_opted_in_at = timezone.now()
        self.app.save()
        data = self.data()
        data["phone"] = "(503) 555-0100"
        self.client.post(self.url, data)
        self.app.refresh_from_db()
        self.assertTrue(resident_can_receive_sms(self.app))

    def test_keep_does_not_clear_opt_out(self):
        stamp = timezone.now()
        self.app.sms_opted_out_at = stamp
        self.app.save()
        self.client.post(self.url, self.data())
        self.app.refresh_from_db()
        self.assertEqual(self.app.sms_opted_out_at, stamp)
        self.assertFalse(resident_can_receive_sms(self.app))

    def test_invalid_phone_cannot_be_saved(self):
        for phone in ["555", "call Aaron", "+445555555555"]:
            data = self.data()
            data["phone"] = phone
            self.assertContains(self.client.post(self.url, data), "Enter a 10-digit")
        self.app.refresh_from_db()
        self.assertEqual(self.app.phone, "+15035550100")

    def test_other_property_is_private(self):
        self.app.property = Property.objects.create(name="Unmanaged")
        self.app.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 404)

    def test_superadmin_resident_inspection_has_contact_editor(self):
        self.staff.role = "admin"
        self.staff.save(update_fields=["role"])
        response = self.client.get(reverse("superadmin_residents"))
        self.assertContains(response, self.url)
        self.assertContains(response, f'{reverse("tenant_dashboard")}?resident={self.app.pk}')

    def test_printable_file_links_to_contact_editor(self):
        self.assertContains(self.client.get(reverse("application_detail", args=[self.app.pk])), self.url)

    def test_resident_cannot_edit_contact_or_consent(self):
        self.client.force_login(self.tenant)
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 302)
        self.app.refresh_from_db()
        self.assertEqual(self.app.phone, "+15035550100")

    def test_staff_can_record_opt_out(self):
        self.app.sms_opted_in = True
        self.app.communication_preference = "sms"
        self.app.save()
        data = self.data()
        data.update(phone=self.app.phone, sms_action="opt_out")
        self.client.post(self.url, data)
        self.app.refresh_from_db()
        self.assertFalse(resident_can_receive_sms(self.app))
        self.assertIsNotNone(self.app.sms_opted_out_at)
        self.assertEqual(self.app.communication_preference, "portal")
