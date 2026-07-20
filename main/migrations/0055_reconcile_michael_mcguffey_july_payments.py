from datetime import date
from decimal import Decimal

from django.db import migrations


def reconcile_michael_july_payments(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")

    july = date(2026, 7, 1)
    residents = HousingApplication.objects.filter(full_name__iregex=r"michael.*mcguffey")
    for resident in residents:
        resident.balance = Decimal("0.00")
        resident.utility_balance = Decimal("0.00")
        resident.deposit_required = Decimal("450.00")
        resident.deposit_paid = Decimal("450.00")
        resident.save(update_fields=[
            "balance",
            "utility_balance",
            "deposit_required",
            "deposit_paid",
        ])

        confirmed_payments = Payment.objects.filter(
            application_id=resident.id,
            status="completed",
        )
        confirmed_payments.filter(
            payment_type="rent",
            amount=Decimal("650.00"),
            service_month__isnull=True,
        ).update(service_month=july)
        confirmed_payments.filter(
            payment_type="utility",
            amount=Decimal("55.00"),
            service_month__isnull=True,
        ).update(service_month=july)
        confirmed_payments.filter(
            payment_type="deposit",
            amount=Decimal("450.00"),
            service_month__isnull=True,
        ).update(service_month=july)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0054_restore_aaron_brown_may_june_room_r"),
    ]

    operations = [
        migrations.RunPython(reconcile_michael_july_payments, noop_reverse),
    ]
