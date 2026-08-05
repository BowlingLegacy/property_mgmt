from datetime import date
from decimal import Decimal

from django.db import migrations


def correct_mitchell_august_charges(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    PropertyRoomRent = apps.get_model("main", "PropertyRoomRent")
    RentHistory = apps.get_model("main", "RentHistory")

    for resident in HousingApplication.objects.filter(full_name__iregex=r"mitchell.*brent"):
        resident.monthly_rent = Decimal("650.00")
        resident.utility_monthly = Decimal("55.00")
        # These values were created by the former automatic-proration behavior.
        # Zero means the normal monthly amounts apply for the lease-start month.
        resident.move_in_rent_charge = Decimal("0.00")
        resident.move_in_utility_charge = Decimal("0.00")
        resident.save(update_fields=[
            "monthly_rent",
            "utility_monthly",
            "move_in_rent_charge",
            "move_in_utility_charge",
        ])

        RentHistory.objects.update_or_create(
            application_id=resident.id,
            effective_date=resident.lease_start_date.replace(day=1) if resident.lease_start_date else date(2026, 8, 1),
            defaults={"rent_amount": Decimal("650.00")},
        )

        if resident.property_id and resident.space_label:
            clean_room = resident.space_label.strip()
            if clean_room.lower().startswith("room "):
                clean_room = clean_room[5:].strip()
            PropertyRoomRent.objects.filter(
                property_id=resident.property_id,
                room_unit_label__in=[clean_room, f"Room {clean_room}"],
            ).update(monthly_rent=Decimal("650.00"), utility_monthly=Decimal("55.00"))


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0056_reconcile_july_2026_rent_roll")]

    operations = [migrations.RunPython(correct_mitchell_august_charges, noop_reverse)]
