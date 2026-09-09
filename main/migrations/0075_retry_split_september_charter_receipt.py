from decimal import Decimal

from django.db import migrations


SPLIT_LINES = (
    ("Cable", Decimal("152.57"), "Spectrum Business TV and cable franchise fee"),
    ("Internet", Decimal("104.00"), "Spectrum Business Internet"),
    ("Communications", Decimal("24.81"), "Spectrum Business Voice and regulatory fees"),
    ("Account Fees", Decimal("10.00"), "Spectrum payment processing charge"),
)


def split_charter_receipt(apps, schema_editor):
    AccountingReceipt = apps.get_model("main", "AccountingReceipt")
    AccountingReceiptSplit = apps.get_model("main", "AccountingReceiptSplit")
    ExpenseCategory = apps.get_model("main", "ExpenseCategory")
    FinancialEntry = apps.get_model("main", "FinancialEntry")

    receipt = AccountingReceipt.objects.filter(
        id=40,
        vendor__iexact="Spectrum",
        amount=Decimal("291.38"),
    ).first()
    if not receipt or receipt.splits.exists() or not receipt.financial_entry_id:
        return

    original_entry = FinancialEntry.objects.get(id=receipt.financial_entry_id)
    receipt.financial_entry_id = None
    receipt.category_id = None
    receipt.description = "September 2026 Spectrum services"
    receipt.save(update_fields=["financial_entry", "category", "description"])

    for index, (category_name, amount, description) in enumerate(SPLIT_LINES, start=1):
        category, _created = ExpenseCategory.objects.get_or_create(
            name=category_name,
            defaults={"entry_type": "operating_expense", "is_active": True},
        )
        if index == 1:
            entry = original_entry
            entry.sheet_name = "Receipt Split"
            entry.row_number = (receipt.id * 1000) + index
            entry.entry_type = "operating_expense"
            entry.category = category_name
            entry.description = description
            entry.amount = amount
            entry.save(update_fields=[
                "sheet_name", "row_number", "entry_type", "category", "description", "amount",
            ])
        else:
            entry = FinancialEntry.objects.create(
                upload_id=original_entry.upload_id,
                ledger_scope=original_entry.ledger_scope,
                property_name=original_entry.property_name,
                sheet_name="Receipt Split",
                row_number=(receipt.id * 1000) + index,
                entry_date=original_entry.entry_date,
                month=original_entry.month,
                year=original_entry.year,
                entry_type="operating_expense",
                category=category_name,
                description=description,
                amount=amount,
            )
        AccountingReceiptSplit.objects.create(
            receipt_id=receipt.id,
            category_id=category.id,
            entry_type="operating_expense",
            description=description,
            amount=amount,
            financial_entry_id=entry.id,
            created_by_id=receipt.reviewed_by_id,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0074_split_september_2026_charter_bill")]

    operations = [migrations.RunPython(split_charter_receipt, noop_reverse)]
