from datetime import date
from decimal import Decimal

from django.db import migrations
from django.utils import timezone


PAYMENT_MARKER = "Aaron Brian Brown $400 payment allocated by migration 0050"


def correct_aaron_brian_brown(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")
    RentHistory = apps.get_model("main", "RentHistory")

    june = date(2026, 6, 1)
    july = date(2026, 7, 1)

    for resident in HousingApplication.objects.filter(full_name__iexact="Aaron Brian Brown"):
        resident.monthly_rent = Decimal("650.00")
        resident.balance = Decimal("0.00")
        resident.utility_monthly = Decimal("55.00")
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
            effective_date=june,
            defaults={"rent_amount": Decimal("650.00")},
        )

        allocations = (
            (june, Decimal("350.00"), "June 2026 rent balance paid in full"),
            (july, Decimal("50.00"), "July 2026 partial rent payment"),
        )
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


def reverse_payment(apps, schema_editor):
    Payment = apps.get_model("main", "Payment")
    Payment.objects.filter(notes=PAYMENT_MARKER).delete()


class Migration(migrations.Migration):
    dependencies = [("main", "0049_record_aaron_brown_payment")]

    operations = [
        migrations.RunPython(correct_aaron_brian_brown, reverse_payment),
    ]
