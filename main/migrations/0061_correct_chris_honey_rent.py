from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Q


RENT = Decimal("600.00")
AUGUST = date(2026, 8, 1)


def correct_chris_honey_rent(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    PropertyRoomRent = apps.get_model("main", "PropertyRoomRent")
    RentHistory = apps.get_model("main", "RentHistory")

    resident = (
        HousingApplication.objects
        .filter(full_name__iexact="Chris Honey", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if not resident:
        return

    resident.monthly_rent = RENT
    resident.move_in_rent_charge = Decimal("0.00")
    resident.save(update_fields=["monthly_rent", "move_in_rent_charge"])

    RentHistory.objects.update_or_create(
        application_id=resident.id,
        effective_date=AUGUST,
        defaults={"rent_amount": RENT},
    )

    PropertyRoomRent.objects.filter(property_id=resident.property_id).filter(
        Q(room_unit_label__iexact="Q") | Q(room_unit_label__iexact="Room Q")
    ).update(monthly_rent=RENT)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0060_reconcile_arjen_august_combined_payment")]

    operations = [migrations.RunPython(correct_chris_honey_rent, noop_reverse)]
