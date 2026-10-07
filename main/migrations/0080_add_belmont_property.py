from django.db import migrations


BELMONT_DESCRIPTION = (
    "Belmont is an established residential duplex in Eugene's Santa Clara area. "
    "The property includes two three-bedroom, one-bath homes, each with a single-car "
    "garage, along with an extra-large backyard. Belmont represents the conventional "
    "long-term housing side of the Bowling Legacy portfolio. Residents maintain their "
    "own power, utility, and garbage accounts. Both homes are currently occupied, and "
    "the exact addresses are withheld from the public listing to respect resident privacy."
)


def add_belmont_property(apps, schema_editor):
    Property = apps.get_model("main", "Property")
    PropertyImage = apps.get_model("main", "PropertyImage")

    property_obj, _created = Property.objects.update_or_create(
        name="Belmont",
        defaults={
            "address": "Santa Clara area, Eugene, Oregon",
            "description": BELMONT_DESCRIPTION,
            "photo": "property_photos/belmont-front-privacy-safe.png",
            "unit_size": "Two 3-bedroom, 1-bath homes",
            "cable_ready": True,
            "available_date": None,
            "deposit_amount": None,
            "rent_amount": None,
            "lease_type": "month_to_month",
            "move_in_cost_type": "other",
            "move_in_cost_notes": "Not publicly listed",
            "utilities_cost": "Residents pay power, utilities, and garbage",
            "availability_status": "full",
            "availability_message": "Both homes are currently occupied",
        },
    )
    PropertyImage.objects.update_or_create(
        property=property_obj,
        image="property_photos/belmont-side-privacy-safe.png",
        defaults={"caption": "Belmont duplex side entry and garden"},
    )


class Migration(migrations.Migration):
    dependencies = [("main", "0079_update_painted_lady_october_availability")]

    operations = [migrations.RunPython(add_belmont_property, migrations.RunPython.noop)]
