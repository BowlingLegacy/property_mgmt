from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Q


SHERRY_PAYMENT = Decimal("880.47")
MONTHLY_DEBT_PAYMENT = Decimal("4000.00")


def reclassify_sherry_payments(apps, schema_editor):
    FinancialEntry = apps.get_model("main", "FinancialEntry")
    ExpenseCategory = apps.get_model("main", "ExpenseCategory")
    AccountingReceipt = apps.get_model("main", "AccountingReceipt")
    AccountingReceiptSplit = apps.get_model("main", "AccountingReceiptSplit")

    candidates = FinancialEntry.objects.filter(amount=SHERRY_PAYMENT).filter(
        Q(year=2026, month__gte=3)
        | Q(entry_date__year=2026, entry_date__month__gte=3)
    ).filter(
        Q(category__icontains="insurance")
        | Q(description__icontains="insurance")
        | Q(description__icontains="sherry")
    )

    candidate_rows = list(candidates.order_by("entry_date", "month", "id"))
    if not candidate_rows:
        return

    debt_category, _created = ExpenseCategory.objects.get_or_create(
        name="Debt Service - Sherry",
        defaults={"entry_type": "debt_service", "is_active": True},
    )
    if debt_category.entry_type != "debt_service" or not debt_category.is_active:
        debt_category.entry_type = "debt_service"
        debt_category.is_active = True
        debt_category.save(update_fields=["entry_type", "is_active"])

    candidate_ids = [entry.id for entry in candidate_rows]
    FinancialEntry.objects.filter(id__in=candidate_ids).update(
        entry_type="debt_service",
        category="Debt Service - Sherry",
        description="Automatic payment to Sherry",
    )
    AccountingReceipt.objects.filter(financial_entry_id__in=candidate_ids).update(
        entry_type="debt_service",
        category_id=debt_category.id,
        vendor="Sherry",
        description="Automatic payment to Sherry",
    )
    AccountingReceiptSplit.objects.filter(financial_entry_id__in=candidate_ids).update(
        entry_type="debt_service",
        category_id=debt_category.id,
        description="Automatic payment to Sherry",
    )

    reference = candidate_rows[-1]
    property_name = reference.property_name
    june_scope = FinancialEntry.objects.filter(
        Q(upload__property_id=reference.upload.property_id)
        | Q(property_name=property_name)
    ).filter(
        Q(year=2026, month=6) | Q(entry_date__year=2026, entry_date__month=6)
    )
    if not june_scope.filter(entry_type="debt_service", amount=MONTHLY_DEBT_PAYMENT).exists():
        FinancialEntry.objects.create(
            upload_id=reference.upload_id,
            ledger_scope=reference.ledger_scope,
            property_name=property_name,
            sheet_name="Debt Service Corrections",
            row_number=0,
            entry_date=date(2026, 6, 1),
            month=6,
            year=2026,
            entry_type="debt_service",
            category="Debt Service",
            description="June 2026 automatic debt service payment",
            amount=MONTHLY_DEBT_PAYMENT,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0063_correct_rooms_i_and_j_occupancy")]

    operations = [migrations.RunPython(reclassify_sherry_payments, noop_reverse)]
