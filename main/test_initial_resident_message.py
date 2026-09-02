from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import HousingApplication, Property, ResidentMessage, User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="office@example.com",
    SMS_PROVIDER="",
)
class InitialResidentMessageTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            username="message-landlord",
            email="landlord@example.com",
            password="StrongPass123!",
            role="landlord",
            is_staff=True,
        )
        self.property = Property.objects.create(
            name="Message Property",
            landlord_email=self.landlord.email,
        )
        self.resident_user = User.objects.create_user(
            username="message-resident",
            email="resident@example.com",
            password="StrongPass123!",
            role="tenant",
        )
        self.resident = HousingApplication.objects.create(
            property=self.property,
            user=self.resident_user,
            full_name="Resident Example",
            email=self.resident_user.email,
            phone="5415550100",
            age=40,
            space_type="Room",
            space_label="A",
            income_source="Employment",
            monthly_income="2500.00",
            housing_need="Current resident",
            tenancy_status="active",
        )
        self.client.login(username=self.landlord.username, password="StrongPass123!")

    def test_staff_can_start_private_resident_message(self):
        response = self.client.post(reverse("landlord_new_resident_message"), {
            "resident": self.resident.id,
            "subject": "Scheduled inspection",
            "message": "Please review the inspection date in your portal.",
        })

        resident_message = ResidentMessage.objects.get()
        self.assertRedirects(
            response,
            reverse("landlord_message_detail", args=[resident_message.id]),
        )
        self.assertEqual(resident_message.application, self.resident)
        self.assertEqual(resident_message.status, "reviewed")
        self.assertEqual(resident_message.subject, "Scheduled inspection")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.resident.email])
        self.assertNotIn(resident_message.message, mail.outbox[0].body)

        self.client.logout()
        self.client.login(username=self.resident_user.username, password="StrongPass123!")
        portal_response = self.client.get(reverse("resident_requests"))
        self.assertContains(portal_response, "Scheduled inspection")
        self.assertContains(portal_response, "Please review the inspection date in your portal.")

    def test_staff_cannot_message_resident_outside_managed_properties(self):
        other_property = Property.objects.create(
            name="Other Property",
            landlord_email="other-landlord@example.com",
        )
        other_resident = HousingApplication.objects.create(
            property=other_property,
            user=User.objects.create_user(username="other-resident", role="tenant"),
            full_name="Other Resident",
            phone="5415550199",
            age=35,
            space_type="Room",
            space_label="B",
            income_source="Employment",
            monthly_income="2400.00",
            housing_need="Current resident",
            tenancy_status="active",
        )

        response = self.client.post(reverse("landlord_new_resident_message"), {
            "resident": other_resident.id,
            "subject": "Should not send",
            "message": "This resident is outside the managed property.",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "resident", "Select a valid choice. That choice is not one of the available choices.")
        self.assertFalse(ResidentMessage.objects.exists())
