from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class DashboardReturnNavigationTests(TestCase):
    def create_user(self, username, role, *, is_staff=False):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="StrongPass123!",
            role=role,
            is_staff=is_staff,
        )

    def test_receipt_page_returns_to_landlord_dashboard_origin(self):
        user = self.create_user("receipt-landlord", "landlord", is_staff=True)
        self.client.force_login(user)

        self.client.get(reverse("landlord_dashboard"))
        response = self.client.get(reverse("accounting_receipts"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_return_url"], reverse("landlord_dashboard"))
        self.assertContains(response, "Return to Landlord Dashboard")

    def test_custom_reports_returns_to_superadmin_dashboard_origin(self):
        user = self.create_user("report-admin", "admin", is_staff=True)
        self.client.force_login(user)

        self.client.get(reverse("superadmin_dashboard"))
        response = self.client.get(reverse("custom_reports"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_return_url"], reverse("superadmin_dashboard"))
        self.assertContains(response, "Return to Super Admin Dashboard")
        self.assertNotContains(response, ">Owner Dashboard</a>")
        self.assertNotContains(response, ">Landlord Dashboard</a>")

    def test_immediate_dashboard_referrer_wins_over_older_session_origin(self):
        user = self.create_user("switching-admin", "admin", is_staff=True)
        self.client.force_login(user)
        self.client.get(reverse("landlord_dashboard"))

        response = self.client.get(
            reverse("custom_reports"),
            HTTP_REFERER=f"http://testserver{reverse('superadmin_dashboard')}",
        )

        self.assertEqual(response.context["dashboard_return_url"], reverse("superadmin_dashboard"))
        self.assertContains(response, "Return to Super Admin Dashboard")

    def test_direct_page_visit_falls_back_to_users_dashboard(self):
        user = self.create_user("direct-owner", "property_owner")
        self.client.force_login(user)

        response = self.client.get(reverse("custom_reports"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_return_url"], reverse("property_owner_dashboard"))
        self.assertContains(response, "Return to Owner Dashboard")

    def test_dashboard_page_does_not_show_return_control(self):
        user = self.create_user("plain-landlord", "landlord", is_staff=True)
        self.client.force_login(user)

        response = self.client.get(reverse("landlord_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["show_dashboard_return"])
        self.assertNotContains(response, "data-dashboard-return")

    def test_standalone_operational_page_gets_the_same_return_control(self):
        user = self.create_user("payment-admin", "admin", is_staff=True)
        self.client.force_login(user)
        self.client.get(reverse("superadmin_dashboard"))

        response = self.client.get(reverse("payment_log"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Return to Super Admin Dashboard")
        self.assertContains(response, "data-dashboard-return style=", count=1)
