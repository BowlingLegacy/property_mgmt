from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def correct_aaron_brown_ledger(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")
    RentHistory = apps.get_model("main", "RentHistory")

    june_start = date(2026, 6, 1)
    july_start = date(2026, 7, 1)
    monthly_rent = Decimal("650.00")
    july_utilities = Decimal("55.00")

    for resident in HousingApplication.objects.filter(full_name__iexact="Aaron Brown"):
        june_rent_paid = (
            Payment.objects.filter(
                application_id=resident.id,
                status="completed",
                payment_type="rent",
                service_month__gte=june_start,
                service_month__lt=july_start,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        resident.monthly_rent = monthly_rent
        resident.balance = max(monthly_rent - june_rent_paid, Decimal("0.00"))
        resident.utility_monthly = july_utilities
        resident.utility_balance = Decimal("0.00")
        resident.deposit_required = Decimal("0.00")
        resident.save(update_fields=[
            "monthly_rent",
            "balance",
            "utility_monthly",
            "utility_balance",
            "deposit_required",
        ])

        RentHistory.objects.update_or_create(
            application_id=resident.id,
            effective_date=june_start,
            defaults={"rent_amount": monthly_rent},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0047_correct_aaron_brown_rent")]

    operations = [
        migrations.RunPython(correct_aaron_brown_ledger, noop_reverse),
    ]
