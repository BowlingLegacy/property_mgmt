import importlib
from datetime import date
from decimal import Decimal

from django.apps import apps as django_apps
from django.test import TestCase
from django.utils import timezone

from .models import (
    CurrentResidentRosterEntry,
    HousingApplication,
    Payment,
    Property,
    PropertyRoomRent,
    User,
)


class RestoreAaronBrownTests(TestCase):
    def test_canceled_move_out_restores_active_room_n_without_changing_finances(self):
        property_obj = Property.objects.create(name="The Painted Lady Inn")
        PropertyRoomRent.objects.create(
            property=property_obj,
            room_unit_label="N",
            monthly_rent=Decimal("650.00"),
            utility_monthly=Decimal("55.00"),
        )
        user = User.objects.create_user(
            username="aaron-restore",
            password="StrongPass123!",
            role="tenant",
            is_active=False,
        )
        resident = HousingApplication.objects.create(
            property=property_obj,
            user=user,
            full_name="Aaron Brian Brown",
            phone="555-0177",
            email="aaron-restore@example.com",
            age=50,
            space_label="",
            monthly_rent=Decimal("650.00"),
            balance=Decimal("325.00"),
            utility_monthly=Decimal("55.00"),
            utility_balance=Decimal("20.00"),
            tenancy_status="former",
            application_folder="archived",
            move_out_date=date(2026, 10, 15),
            former_tenant_archived_at=timezone.now(),
            tenancy_end_reason="Planned move-out",
            tenancy_archive_notes="Original move-out record",
            income_source="Employment",
            monthly_income=Decimal("2500.00"),
            housing_need="Current resident.",
        )
        payment = Payment.objects.create(
            application=resident,
            payment_type="rent",
            payment_method="cash",
            amount=Decimal("325.00"),
            status="completed",
            service_month=date(2026, 10, 1),
        )
        roster = CurrentResidentRosterEntry.objects.create(
            property=property_obj,
            first_name="Aaron",
            last_name="Brown",
            email=resident.email,
            phone=resident.phone,
            room_unit_label="R",
            is_active=False,
        )

        migration = importlib.import_module(
            "main.migrations.0082_restore_aaron_brown_active_room_n"
        )
        migration.restore_aaron_brown(django_apps, None)

        resident.refresh_from_db()
        user.refresh_from_db()
        roster.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(resident.tenancy_status, "active")
        self.assertEqual(resident.application_folder, "active")
        self.assertEqual(resident.space_label, "N")
        self.assertIsNone(resident.move_out_date)
        self.assertIsNone(resident.former_tenant_archived_at)
        self.assertEqual(resident.tenancy_end_reason, "")
        self.assertEqual(resident.tenancy_archive_notes, "")
        self.assertTrue(user.is_active)
        self.assertTrue(roster.is_active)
        self.assertEqual(roster.room_unit_label, "N")
        self.assertEqual(resident.balance, Decimal("325.00"))
        self.assertEqual(resident.utility_balance, Decimal("20.00"))
        self.assertEqual(payment.amount, Decimal("325.00"))
