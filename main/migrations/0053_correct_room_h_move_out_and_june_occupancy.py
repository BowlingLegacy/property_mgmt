from datetime import date
from decimal import Decimal

from django.db import migrations


def correct_room_h_history(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    RentRollSnapshot = apps.get_model("main", "RentRollSnapshot")

    june = date(2026, 6, 1)
    nick_records = HousingApplication.objects.filter(full_name__iregex=r"nick.*lyle")

    for resident in nick_records:
        resident.balance = Decimal("295.00")
        resident.utility_balance = Decimal("220.00")
        resident.deposit_required = Decimal("450.00")
        resident.deposit_paid = Decimal("0.00")
        resident.save(update_fields=[
            "balance",
            "utility_balance",
            "deposit_required",
            "deposit_paid",
        ])

        RentRollSnapshot.objects.filter(
            property_id=resident.property_id,
            service_month=june,
            application_id=resident.id,
        ).delete()

    for felicia in HousingApplication.objects.filter(full_name__iexact="Felicia Valdez"):
        if not felicia.property_id:
            continue

        RentRollSnapshot.objects.filter(
            property_id=felicia.property_id,
            service_month=june,
            room_unit_label__iexact="H",
        ).delete()
        RentRollSnapshot.objects.create(
            property_id=felicia.property_id,
            application_id=felicia.id,
            service_month=june,
            room_unit_label="H",
            resident_name=felicia.full_name,
            monthly_rent=felicia.monthly_rent,
            rent_charge=felicia.monthly_rent,
            utility_monthly=felicia.utility_monthly,
            utility_charge=felicia.utility_monthly,
            deposit_required=felicia.deposit_required,
            deposit_paid=felicia.deposit_paid,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0052_rent_roll_snapshot")]

    operations = [
        migrations.RunPython(correct_room_h_history, noop_reverse),
    ]
