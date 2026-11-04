from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0093_financialupload_file_path_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="is_public",
            field=models.BooleanField(
                default=True,
                help_text="Show this property on the public website.",
            ),
        ),
    ]
