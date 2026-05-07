from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("main", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResidentMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "message_type",
                    models.CharField(
                        choices=[
                            ("maintenance", "Maintenance Request"),
                            ("complaint", "Complaint"),
                            ("general", "General Message"),
                            ("document", "Document Question"),
                        ],
                        default="general",
                        max_length=30,
                    ),
                ),
                (
                    "subject",
                    models.CharField(max_length=255),
                ),
                (
                    "message",
                    models.TextField(),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("reviewed", "Reviewed"),
                            ("closed", "Closed"),
                        ],
                        default="submitted",
                        max_length=30,
                    ),
                ),
                (
                    "locked",
                    models.BooleanField(default=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resident_messages",
                        to="main.housingapplication",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
