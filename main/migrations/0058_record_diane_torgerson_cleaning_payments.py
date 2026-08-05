from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum
from django.utils import timezone


MONTHS = tuple(date(2026, month, 1) for month in range(1, 9))
RENT = Decimal("500.00")
DEFAULT_UTILITIES = Decimal("55.00")
MARKER = "Diane Torgerson cleaning-services credit migration 0058"


def ensure_cleaning_credit(Payment, resident, payment_type, amount, service_month):
    already_paid = (
        Payment.objects.filter(
            application_id=resident.id,
            payment_type=payment_type,
            service_month=service_month,
            status="completed",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    difference = max(amount - already_paid, Decimal("0.00"))
    if difference:
        Payment.objects.create(
            application_id=resident.id,
            payment_type=payment_type,
            payment_method="other",
            amount=difference,
            status="completed",
            received_at=timezone.now(),
            service_month=service_month,
            months_covered=1,
            description=f"{service_month.strftime('%B %Y')} {payment_type} paid by cleaning services",
            reference_number=f"CLEANING-SERVICES-{service_month:%Y-%m}-{payment_type.upper()}",
            notes=MARKER,
        )


def record_diane_cleaning_payments(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")
    RentHistory = apps.get_model("main", "RentHistory")

    resident = (
        HousingApplication.objects
        .filter(full_name__iexact="Diane Torgerson", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if not resident:
        return

    utilities = resident.utility_monthly or DEFAULT_UTILITIES
    if utilities <= 0:
        utilities = DEFAULT_UTILITIES

    resident.monthly_rent = RENT
    resident.utility_monthly = utilities
    resident.balance = Decimal("0.00")
    resident.utility_balance = Decimal("0.00")
    resident.save(update_fields=["monthly_rent", "utility_monthly", "balance", "utility_balance"])

    RentHistory.objects.update_or_create(
        application_id=resident.id,
        effective_date=MONTHS[0],
        defaults={"rent_amount": RENT},
    )

    for service_month in MONTHS:
        ensure_cleaning_credit(Payment, resident, "rent", RENT, service_month)
        ensure_cleaning_credit(Payment, resident, "utility", utilities, service_month)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0057_correct_mitchell_brent_august_charges")]

    operations = [migrations.RunPython(record_diane_cleaning_payments, noop_reverse)]
