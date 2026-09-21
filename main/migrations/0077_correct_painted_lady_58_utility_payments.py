from decimal import Decimal

from django.db import migrations


PROPERTY_NAME = "The Painted Lady Inn"
INCORRECT_AMOUNT = Decimal("58.00")
CORRECT_AMOUNT = Decimal("55.00")
MARKER = "Corrected utility payment from $58.00 to $55.00 by migration 0077."


def correct_utility_payments(apps, schema_editor):
    Payment = apps.get_model("main", "Payment")

    payments = Payment.objects.filter(
        application__property__name__iexact=PROPERTY_NAME,
        payment_type="utility",
        payment_method="cash",
        status="completed",
        amount=INCORRECT_AMOUNT,
        reference_number="",
    )

    for payment in payments.iterator():
        payment.amount = CORRECT_AMOUNT
        payment.notes = f"{payment.notes}\n\n{MARKER}" if payment.notes else MARKER
        payment.save(update_fields=["amount", "notes"])


class Migration(migrations.Migration):
    dependencies = [("main", "0076_correct_and_split_july_2026_spectrum_bill")]

    operations = [migrations.RunPython(correct_utility_payments, migrations.RunPython.noop)]
