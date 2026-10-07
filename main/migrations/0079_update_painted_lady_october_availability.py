from datetime import date

from django.db import migrations


PAINTED_LADY_NAMES = ("The Painted Lady Inn", "Painted Lady Inn")


def update_painted_lady_availability(apps, schema_editor):
    Property = apps.get_model("main", "Property")

    for property_name in PAINTED_LADY_NAMES:
        Property.objects.filter(name__iexact=property_name).update(
            unit_size="Single occupancy",
            available_date=date(2026, 10, 15),
            availability_status="waitlist",
            availability_message="Single-occupancy room available October 15, 2026",
        )


class Migration(migrations.Migration):
    dependencies = [("main", "0078_restore_painted_lady_58_utility_payments")]

    operations = [
        migrations.RunPython(update_painted_lady_availability, migrations.RunPython.noop),
    ]
