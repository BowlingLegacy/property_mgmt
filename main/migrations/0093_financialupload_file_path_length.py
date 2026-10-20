from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0092_tenant_document_messages"),
    ]

    operations = [
        migrations.AlterField(
            model_name="financialupload",
            name="file",
            field=models.FileField(upload_to="financial_uploads/", max_length=255),
        ),
    ]
