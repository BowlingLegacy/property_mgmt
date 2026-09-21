from decimal import Decimal

from django.db import migrations


CORRECTION_MARKER = "Corrected utility payment from $58.00 to $55.00 by migration 0077."
RESTORE_MARKER = "Restored utility payment to $58.00 by migration 0078."


def restore_utility_payments(apps, schema_editor):
    Payment = apps.get_model("main", "Payment")

    payments = Payment.objects.filter(
        amount=Decimal("55.00"),
        notes__contains=CORRECTION_MARKER,
    )
    for payment in payments.iterator():
        payment.amount = Decimal("58.00")
        payment.notes = f"{payment.notes}\n\n{RESTORE_MARKER}"
        payment.save(update_fields=["amount", "notes"])


class Migration(migrations.Migration):
    dependencies = [("main", "0077_correct_painted_lady_58_utility_payments")]

    operations = [migrations.RunPython(restore_utility_payments, migrations.RunPython.noop)]
