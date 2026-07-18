from datetime import date
from decimal import Decimal

from django.db import migrations
from django.utils import timezone


PAYMENT_MARKER = "Aaron Brown $400 payment allocated by migration 0049"


def record_aaron_brown_payment(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")

    allocations = (
        (date(2026, 6, 1), Decimal("350.00"), "June 2026 rent balance"),
        (date(2026, 7, 1), Decimal("50.00"), "July 2026 partial rent"),
    )

    for resident in HousingApplication.objects.filter(full_name__iexact="Aaron Brown"):
        for service_month, amount, description in allocations:
            Payment.objects.get_or_create(
                application_id=resident.id,
                payment_type="rent",
                status="completed",
                service_month=service_month,
                amount=amount,
                notes=PAYMENT_MARKER,
                defaults={
                    "payment_method": "other",
                    "description": description,
                    "received_at": timezone.now(),
                    "months_covered": 1,
                },
            )

        # The $350 June allocation satisfies the carried balance. July's $50
        # allocation is reported against July's scheduled $650 rent.
        resident.balance = Decimal("0.00")
        resident.save(update_fields=["balance"])


def remove_aaron_brown_payment(apps, schema_editor):
    Payment = apps.get_model("main", "Payment")
    Payment.objects.filter(notes=PAYMENT_MARKER).delete()


class Migration(migrations.Migration):
    dependencies = [("main", "0048_correct_aaron_brown_ledger")]

    operations = [
        migrations.RunPython(record_aaron_brown_payment, remove_aaron_brown_payment),
    ]
