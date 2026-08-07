from django.db import migrations, models


def ensure_cleaning_labor_category(apps, schema_editor):
    ExpenseCategory = apps.get_model("main", "ExpenseCategory")
    category, _created = ExpenseCategory.objects.get_or_create(
        name="Cleaning Labor",
        defaults={"entry_type": "operating_expense", "is_active": True},
    )
    if category.entry_type != "operating_expense" or not category.is_active:
        category.entry_type = "operating_expense"
        category.is_active = True
        category.save(update_fields=["entry_type", "is_active"])


class Migration(migrations.Migration):
    dependencies = [("main", "0068_correct_chris_a_honey_rent")]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("stripe_card", "Stripe Card"),
                    ("stripe_cashapp", "Stripe Cash App Pay"),
                    ("bank_transfer", "Bank Transfer"),
                    ("cashapp", "Cash App"),
                    ("cash", "Cash"),
                    ("check", "Check"),
                    ("money_order", "Money Order"),
                    ("zelle", "Zelle"),
                    ("ach", "ACH"),
                    ("service_credit", "Service / Labor Credit"),
                    ("other", "Other"),
                ],
                default="stripe_card",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="accountingreceipt",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("stripe_card", "Stripe Card"),
                    ("stripe_cashapp", "Stripe Cash App Pay"),
                    ("bank_transfer", "Bank Transfer"),
                    ("cashapp", "Cash App"),
                    ("cash", "Cash"),
                    ("check", "Check"),
                    ("money_order", "Money Order"),
                    ("zelle", "Zelle"),
                    ("ach", "ACH"),
                    ("service_credit", "Service / Labor Credit"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=30,
            ),
        ),
        migrations.RunPython(ensure_cleaning_labor_category, migrations.RunPython.noop),
    ]
