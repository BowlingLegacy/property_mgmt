from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def correct_aaron_brown_rent(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")
    RentHistory = apps.get_model("main", "RentHistory")

    june_start = date(2026, 6, 1)
    july_start = date(2026, 7, 1)
    corrected_rent = Decimal("650.00")

    residents = HousingApplication.objects.filter(full_name__iexact="Aaron Brown")
    for resident in residents:
        resident.monthly_rent = corrected_rent

        june_paid = (
            Payment.objects.filter(
                application_id=resident.id,
                status="completed",
                payment_type="rent",
                service_month__gte=june_start,
                service_month__lt=july_start,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        june_unpaid = max(corrected_rent - june_paid, Decimal("0.00"))
        resident.balance = max(resident.balance or Decimal("0.00"), june_unpaid)
        resident.save(update_fields=["monthly_rent", "balance"])

        RentHistory.objects.update_or_create(
            application_id=resident.id,
            effective_date=june_start,
            defaults={"rent_amount": corrected_rent},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0046_application_identity_vehicle")]

    operations = [
        migrations.RunPython(correct_aaron_brown_rent, noop_reverse),
    ]
