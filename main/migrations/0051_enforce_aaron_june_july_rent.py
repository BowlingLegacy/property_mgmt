from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Q


def enforce_aaron_june_july_rent(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    PropertyRoomRent = apps.get_model("main", "PropertyRoomRent")
    RentHistory = apps.get_model("main", "RentHistory")

    june = date(2026, 6, 1)
    august = date(2026, 8, 1)
    corrected_rent = Decimal("650.00")

    for resident in HousingApplication.objects.filter(full_name__iexact="Aaron Brian Brown"):
        resident.monthly_rent = corrected_rent
        resident.save(update_fields=["monthly_rent"])

        history = RentHistory.objects.filter(
            application_id=resident.id,
            effective_date__gte=june,
            effective_date__lt=august,
        )
        history.update(rent_amount=corrected_rent)
        RentHistory.objects.update_or_create(
            application_id=resident.id,
            effective_date=june,
            defaults={"rent_amount": corrected_rent},
        )

        PropertyRoomRent.objects.filter(property_id=resident.property_id).filter(
            Q(room_unit_label__iexact="N") | Q(room_unit_label__iexact="Room N")
        ).update(monthly_rent=corrected_rent)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0050_correct_aaron_brian_brown")]

    operations = [
        migrations.RunPython(enforce_aaron_june_july_rent, noop_reverse),
    ]
