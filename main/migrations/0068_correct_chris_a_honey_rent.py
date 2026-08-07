from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Q


RENT = Decimal("600.00")
AUGUST = date(2026, 8, 1)


def correct_chris_a_honey_rent(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    PropertyRoomRent = apps.get_model("main", "PropertyRoomRent")
    RentHistory = apps.get_model("main", "RentHistory")

    # Production stores this resident as "Chris A Honey". Match by first and
    # last name so optional middle names cannot prevent future corrections.
    residents = HousingApplication.objects.filter(
        full_name__iregex=r"^Chris.*Honey$",
        property_id__isnull=False,
    )
    property_ids = set(residents.values_list("property_id", flat=True))

    for resident in residents:
        resident.monthly_rent = RENT
        resident.move_in_rent_charge = Decimal("0.00")
        resident.save(update_fields=["monthly_rent", "move_in_rent_charge"])

        RentHistory.objects.filter(application_id=resident.id).update(rent_amount=RENT)
        RentHistory.objects.update_or_create(
            application_id=resident.id,
            effective_date=AUGUST,
            defaults={"rent_amount": RENT},
        )

    for property_id in property_ids:
        PropertyRoomRent.objects.filter(property_id=property_id).filter(
            Q(room_unit_label__iexact="Q") | Q(room_unit_label__iexact="Room Q")
        ).update(monthly_rent=RENT)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0067_enforce_chris_honey_600_rent")]

    operations = [migrations.RunPython(correct_chris_a_honey_rent, noop_reverse)]
