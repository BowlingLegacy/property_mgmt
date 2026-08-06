from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Q


MONTHLY_CLEANING_LABOR = Decimal("555.00")


def add_cleaning_labor_expenses(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    FinancialUpload = apps.get_model("main", "FinancialUpload")
    FinancialEntry = apps.get_model("main", "FinancialEntry")

    diane = (
        HousingApplication.objects
        .filter(full_name__iexact="Diane Torgerson", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if not diane:
        return

    upload, _created = FinancialUpload.objects.get_or_create(
        property_id=diane.property_id,
        name="2026 Cleaning Labor Ledger",
        defaults={
            "ledger_scope": "property",
            "file": "financial_uploads/2026_cleaning_labor_ledger.csv",
            "notes": "Monthly cleaning labor expenses entered by migration 0066.",
        },
    )

    property_name = diane.property.name
    for month in range(1, 9):
        month_entries = FinancialEntry.objects.filter(
            Q(upload__property_id=diane.property_id) | Q(property_name=property_name)
        ).filter(
            Q(year=2026, month=month) | Q(entry_date__year=2026, entry_date__month=month)
        ).filter(
            entry_type="operating_expense",
            amount=MONTHLY_CLEANING_LABOR,
        ).filter(
            Q(category__icontains="cleaning") | Q(description__icontains="cleaning labor")
        )
        if month_entries.exists():
            month_entries.update(category="Cleaning Labor", description="Monthly cleaning labor")
            continue

        FinancialEntry.objects.create(
            upload_id=upload.id,
            ledger_scope="property",
            property_name=property_name,
            sheet_name="Cleaning Labor",
            row_number=month,
            entry_date=date(2026, month, 1),
            month=month,
            year=2026,
            entry_type="operating_expense",
            category="Cleaning Labor",
            description="Monthly cleaning labor",
            amount=MONTHLY_CLEANING_LABOR,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0065_reconcile_mike_dudley_august_payments")]

    operations = [migrations.RunPython(add_cleaning_labor_expenses, noop_reverse)]
