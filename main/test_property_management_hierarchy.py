from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .forms import OwnerLandlordInviteForm
from .models import Property, PropertyOwnerIntake, User


class PropertyManagementHierarchyTests(TestCase):
    password = "StrongPass123!"

    def create_user(self, username, role, email):
        return User.objects.create_user(
            username=username,
            email=email,
            password=self.password,
            role=role,
        )

    def test_owner_created_self_managed_property_uses_owner_as_landlord(self):
        owner = self.create_user("self-owner", "property_owner", "self-owner@example.com")
        self.client.force_login(owner)

        response = self.client.post(reverse("owner_property_create"), {
            "name": "Belmont",
            "management_mode": "owner_managed",
            "lease_type": "month_to_month",
            "move_in_cost_type": "rent_deposit",
            "availability_status": "full",
            "availability_message": "Fully occupied",
        })

        self.assertEqual(response.status_code, 302)
        property_obj = Property.objects.get(name="Belmont", owner_email=owner.email)
        self.assertEqual(property_obj.owner_email, owner.email)
        self.assertEqual(property_obj.landlord_email, owner.email)
        self.assertEqual(property_obj.dashboard_name, "Belmont Dashboard")

    def test_owner_can_change_property_to_management_company(self):
        owner = self.create_user("managed-owner", "property_owner", "managed-owner@example.com")
        property_obj = Property.objects.create(
            name="Painted Lady",
            owner_email=owner.email,
            landlord_email=owner.email,
        )
        self.client.force_login(owner)

        response = self.client.post(reverse("owner_property_edit", args=[property_obj.id]), {
            "name": property_obj.name,
            "management_mode": "management_company",
            "management_company_name": "Reliable Management",
            "management_company_email": "office@reliable.example.com",
            "lease_type": "month_to_month",
            "move_in_cost_type": "rent_deposit",
            "availability_status": "full",
            "availability_message": "Fully occupied",
        })

        self.assertRedirects(response, reverse("property_owner_dashboard"))
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.management_company_email, "office@reliable.example.com")
        self.assertEqual(property_obj.landlord_email, "")

    def test_management_company_sees_only_assigned_owners_and_properties(self):
        manager = self.create_user("management-company", "property_manager", "manager@example.com")
        assigned = Property.objects.create(
            name="Assigned Home",
            owner_email="owner-one@example.com",
            management_mode="management_company",
            management_company_email=manager.email,
        )
        Property.objects.create(
            name="Hidden Home",
            owner_email="owner-two@example.com",
            management_mode="management_company",
            management_company_email="different-manager@example.com",
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("property_management_dashboard"))

        self.assertContains(response, assigned.dashboard_name)
        self.assertContains(response, "owner-one@example.com")
        self.assertNotContains(response, "Hidden Home")

    def test_selected_management_company_workspace_scopes_followup_pages(self):
        manager = self.create_user("scoped-manager", "property_manager", "scoped-manager@example.com")
        first = Property.objects.create(
            name="Belmont",
            owner_email="owner@example.com",
            management_mode="management_company",
            management_company_email=manager.email,
        )
        second = Property.objects.create(
            name="Painted Lady",
            owner_email="owner@example.com",
            management_mode="management_company",
            management_company_email=manager.email,
        )
        self.client.force_login(manager)

        dashboard = self.client.get(reverse("landlord_dashboard"), {"property_id": first.id})
        receipt_workspace = self.client.get(reverse("accounting_receipts"))

        self.assertContains(dashboard, first.dashboard_name)
        self.assertEqual(receipt_workspace.context["selected_property"], first)
        self.assertNotContains(receipt_workspace, second.name)

    def test_landlord_login_is_rejected_when_assigned_to_multiple_properties(self):
        landlord = self.create_user("crossed-landlord", "landlord", "landlord@example.com")
        Property.objects.create(name="First Home", landlord_email=landlord.email)
        Property.objects.create(name="Second Home", landlord_email=landlord.email)
        self.client.force_login(landlord)

        response = self.client.get(reverse("landlord_dashboard"))

        self.assertContains(response, "must be assigned to exactly one property")
        self.assertNotContains(response, "First Home Dashboard")
        self.assertNotContains(response, "Second Home Dashboard")

    def test_property_landlord_has_no_owner_admin_or_expense_import_access(self):
        landlord = self.create_user("isolated-landlord", "landlord", "isolated-landlord@example.com")
        property_obj = Property.objects.create(name="Belmont", landlord_email=landlord.email)
        self.client.force_login(landlord)

        dashboard = self.client.get(reverse("landlord_dashboard"))

        self.assertContains(dashboard, property_obj.dashboard_name)
        self.assertNotContains(dashboard, "Owner Portfolio")
        self.assertNotContains(dashboard, "Super Admin")
        self.assertNotContains(dashboard, "Expense Imports")
        self.assertNotContains(dashboard, ">Dashboard</a>")
        self.assertEqual(self.client.get(reverse("property_owner_dashboard")).status_code, 302)
        self.assertEqual(self.client.get(reverse("superadmin_dashboard")).status_code, 302)
        self.assertEqual(self.client.get(reverse("financial_upload")).status_code, 302)

    def test_landlord_profile_email_cannot_be_reused_for_another_property(self):
        first = Property.objects.create(name="First Home", landlord_email="landlord@example.com")
        second = Property.objects.create(name="Second Home")
        form = OwnerLandlordInviteForm(data={
            "property": second.id,
            "full_name": "Property Landlord",
            "email": first.landlord_email,
            "phone": "",
            "address": "",
        }, properties=Property.objects.all())

        self.assertFalse(form.is_valid())
        self.assertIn("already assigned to another property", form.errors["email"][0])

    @patch("main.views.send_portal_access_invite_email", return_value=True)
    def test_management_company_onboarding_creates_management_portal(self, _send_invite):
        admin = User.objects.create_superuser(
            username="hierarchy-admin", email="admin@example.com", password=self.password, role="admin",
        )
        intake = PropertyOwnerIntake.objects.create(
            portal_type="property_manager",
            full_name="Reliable Management",
            company_name="Reliable Management",
            email="office@reliable.example.com",
            phone="541-555-0100",
        )
        self.client.force_login(admin)

        response = self.client.post(reverse("superadmin_send_owner_invite", args=[intake.id]))

        self.assertRedirects(response, reverse("superadmin_owner_intake_detail", args=[intake.id]))
        intake.refresh_from_db()
        self.assertEqual(intake.user.role, "property_manager")
