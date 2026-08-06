from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum
from django.utils import timezone


AUGUST = date(2026, 8, 1)
MARKER = "Mike Dudley August 2026 payment reconciliation migration 0065"


def ensure_payment(Payment, resident, payment_type, target):
    paid = (
        Payment.objects.filter(
            application_id=resident.id,
            payment_type=payment_type,
            service_month=AUGUST,
            status="completed",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    difference = max(Decimal(target) - paid, Decimal("0.00"))
    if difference:
        Payment.objects.create(
            application_id=resident.id,
            payment_type=payment_type,
            payment_method="other",
            amount=difference,
            status="completed",
            received_at=timezone.now(),
            service_month=AUGUST,
            months_covered=1,
            description=f"August 2026 {payment_type} confirmed paid",
            notes=MARKER,
        )


def reconcile_mike_dudley_august_payments(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")

    resident = (
        HousingApplication.objects
        .filter(full_name__iregex=r"^Mike\s+Dudl(e)?y$", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if not resident:
        return

    rent = resident.monthly_rent or Decimal("0.00")
    utilities = resident.utility_monthly or Decimal("55.00")
    ensure_payment(Payment, resident, "rent", rent)
    ensure_payment(Payment, resident, "utility", utilities)

    resident.balance = Decimal("0.00")
    resident.utility_balance = Decimal("0.00")
    resident.save(update_fields=["balance", "utility_balance"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0064_reclassify_sherry_payments_as_debt_service")]

    operations = [migrations.RunPython(reconcile_mike_dudley_august_payments, noop_reverse)]
