from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


AUGUST = date(2026, 8, 1)
RENT = Decimal("650.00")
UTILITIES = Decimal("55.00")
TOTAL = RENT + UTILITIES
MARKER = "Arjen August 2026 combined payment reconciliation migration 0060"


def reconcile_arjen_august_payment(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")

    resident = (
        HousingApplication.objects
        .filter(full_name__istartswith="Arjen", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if not resident:
        return

    completed = Payment.objects.filter(application_id=resident.id, status="completed")
    rent_paid = completed.filter(payment_type="rent", service_month=AUGUST).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    utility_paid = completed.filter(payment_type="utility", service_month=AUGUST).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    if rent_paid < RENT or utility_paid < UTILITIES:
        combined = completed.filter(amount=TOTAL).order_by("-received_at", "-id").first()
        if combined:
            original_description = combined.description
            combined.payment_type = "rent"
            combined.amount = RENT
            combined.service_month = AUGUST
            combined.months_covered = 1
            combined.description = "August 2026 rent - split from completed $705 payment"
            combined.notes = (combined.notes + "\n\n" if combined.notes else "") + MARKER
            combined.save(update_fields=[
                "payment_type", "amount", "service_month", "months_covered", "description", "notes",
            ])

            utility = completed.filter(
                payment_type="utility", service_month=AUGUST, notes__contains=MARKER
            ).first()
            if not utility:
                Payment.objects.create(
                    application_id=resident.id,
                    payment_type="utility",
                    payment_method=combined.payment_method,
                    amount=UTILITIES,
                    status="completed",
                    recorded_by_id=combined.recorded_by_id,
                    received_at=combined.received_at,
                    service_month=AUGUST,
                    months_covered=1,
                    reference_number=combined.reference_number,
                    description="August 2026 utilities - split from completed $705 payment",
                    notes=f"{MARKER}. Original description: {original_description}",
                )

    resident.balance = Decimal("0.00")
    resident.utility_balance = Decimal("0.00")
    resident.save(update_fields=["balance", "utility_balance"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0059_reconcile_mark_moore_august_payments")]

    operations = [migrations.RunPython(reconcile_arjen_august_payment, noop_reverse)]
