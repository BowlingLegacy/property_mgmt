from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum
from django.utils import timezone


AUGUST = date(2026, 8, 1)
RENT = Decimal("600.00")
MARKER = "Chris A Honey August 2026 rent paid-in-full reconciliation migration 0073"


def complete_chris_august_rent(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")

    resident = (
        HousingApplication.objects
        .filter(full_name__iregex=r"^Chris.*Honey$", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if not resident:
        return

    paid = (
        Payment.objects.filter(
            application_id=resident.id,
            payment_type="rent",
            service_month=AUGUST,
            status="completed",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    difference = max(RENT - paid, Decimal("0.00"))
    if difference:
        Payment.objects.create(
            application_id=resident.id,
            payment_type="rent",
            payment_method="other",
            amount=difference,
            status="completed",
            received_at=timezone.now(),
            service_month=AUGUST,
            months_covered=1,
            reference_number="AUGUST-2026-RENT-RECONCILIATION",
            description="August 2026 rent confirmed paid in full",
            notes=MARKER,
        )

    resident.balance = Decimal("0.00")
    resident.save(update_fields=["balance"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0072_remove_owner_from_all_rent_roll_snapshots")]

    operations = [migrations.RunPython(complete_chris_august_rent, noop_reverse)]
