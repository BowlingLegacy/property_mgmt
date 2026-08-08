from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum
from django.utils import timezone


JULY = date(2026, 7, 1)
CREDIT = Decimal("300.00")
MARKER = "Aaron Brown July 2026 maintenance labor credit migration 0070"


def record_aaron_maintenance_credit(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")
    ExpenseCategory = apps.get_model("main", "ExpenseCategory")
    FinancialUpload = apps.get_model("main", "FinancialUpload")
    FinancialEntry = apps.get_model("main", "FinancialEntry")

    resident = (
        HousingApplication.objects
        .filter(full_name__iregex=r"^Aaron.*Brown$", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if not resident:
        return

    category, _created = ExpenseCategory.objects.get_or_create(
        name="Maintenance Labor",
        defaults={"entry_type": "operating_expense", "is_active": True},
    )
    if category.entry_type != "operating_expense" or not category.is_active:
        category.entry_type = "operating_expense"
        category.is_active = True
        category.save(update_fields=["entry_type", "is_active"])

    existing_credit = (
        Payment.objects.filter(
            application_id=resident.id,
            payment_type="rent",
            payment_method="service_credit",
            service_month=JULY,
            status="completed",
            notes__contains=MARKER,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    difference = max(CREDIT - existing_credit, Decimal("0.00"))
    if difference:
        payment = Payment.objects.create(
            application_id=resident.id,
            payment_type="rent",
            payment_method="service_credit",
            amount=difference,
            status="completed",
            received_at=timezone.now(),
            service_month=JULY,
            months_covered=1,
            reference_number="JULY-2026-MAINTENANCE-CREDIT",
            description="July rent credit for maintenance labor",
            notes=MARKER,
        )

        resident.balance = max((resident.balance or Decimal("0.00")) - difference, Decimal("0.00"))
        resident.save(update_fields=["balance"])

        upload, _created = FinancialUpload.objects.get_or_create(
            property_id=resident.property_id,
            name="Service Credit Ledger",
            defaults={
                "ledger_scope": "property",
                "file": "financial_uploads/service_credit_ledger.csv",
                "notes": "Operating expenses created from rent and utility service credits.",
            },
        )
        FinancialEntry.objects.update_or_create(
            upload_id=upload.id,
            sheet_name="Service Credits",
            row_number=payment.id,
            defaults={
                "ledger_scope": "property",
                "property_name": resident.property.name,
                "entry_date": JULY,
                "month": 7,
                "year": 2026,
                "entry_type": "operating_expense",
                "category": category.name,
                "description": f"Service credit payment #{payment.id} for {resident.full_name}",
                "amount": difference,
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0069_service_credit_payment_method")]

    operations = [migrations.RunPython(record_aaron_maintenance_credit, noop_reverse)]
