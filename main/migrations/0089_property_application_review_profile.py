from decimal import Decimal

from django.db import migrations, models


def configure_known_application_review_profiles(apps, schema_editor):
    Property = apps.get_model("main", "Property")

    Property.objects.filter(name__icontains="painted lady").update(
        application_review_profile="supportive_housing",
    )
    Property.objects.filter(name__icontains="belmont").update(
        application_review_profile="standard_rental",
        charges_application_fee=False,
        application_fee_amount=Decimal("0.00"),
        requires_background_check=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0088_property_management_hierarchy"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="application_review_profile",
            field=models.CharField(
                choices=[
                    ("standard_rental", "Standard whole-property rental"),
                    ("supportive_housing", "Supportive / room-based housing"),
                ],
                default="standard_rental",
                help_text="Controls which application-review framework is used for this property.",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="property",
            name="requires_background_check",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(configure_known_application_review_profiles, migrations.RunPython.noop),
    ]
