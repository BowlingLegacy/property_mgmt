from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Q


def restore_aaron_room_r_snapshots(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    RentRollSnapshot = apps.get_model("main", "RentRollSnapshot")

    residents = HousingApplication.objects.filter(
        Q(full_name__iexact="Aaron Brown")
        | Q(full_name__iexact="Aaron Brian Brown")
    )
    for resident in residents:
        if not resident.property_id:
            continue

        for service_month in (date(2026, 5, 1), date(2026, 6, 1)):
            RentRollSnapshot.objects.filter(
                property_id=resident.property_id,
                service_month=service_month,
            ).filter(
                Q(application_id=resident.id)
                | Q(room_unit_label__iexact="R")
            ).delete()
            RentRollSnapshot.objects.create(
                property_id=resident.property_id,
                application_id=resident.id,
                service_month=service_month,
                room_unit_label="R",
                resident_name=resident.full_name,
                monthly_rent=Decimal("650.00"),
                rent_charge=Decimal("650.00"),
                utility_monthly=Decimal("55.00"),
                utility_charge=Decimal("55.00"),
                deposit_required=Decimal("0.00"),
                deposit_paid=Decimal("0.00"),
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0053_correct_room_h_move_out_and_june_occupancy"),
    ]

    operations = [
        migrations.RunPython(restore_aaron_room_r_snapshots, noop_reverse),
    ]
