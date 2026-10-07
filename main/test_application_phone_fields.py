from django.test import TestCase
from django.urls import reverse


class ApplicationPhoneFieldTests(TestCase):
    def test_public_application_phone_fields_do_not_show_personal_number(self):
        response = self.client.get(reverse("apply"))

        self.assertEqual(response.status_code, 200)
        phone_field = response.context["form"]["phone"]
        self.assertIsNone(phone_field.value())
        self.assertEqual(phone_field.field.widget.attrs["placeholder"], "Applicant phone number")
        self.assertNotContains(response, "(541) 326-8047")
