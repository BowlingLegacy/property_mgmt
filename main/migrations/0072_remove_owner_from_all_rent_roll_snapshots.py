from django.db import migrations
from django.db.models.functions import Lower, Replace, Trim
from django.db.models import Value


def remove_owner_snapshots(apps, schema_editor):
    RentRollSnapshot = apps.get_model("main", "RentRollSnapshot")
    normalized = RentRollSnapshot.objects.annotate(
        normalized_room=Lower(
            Replace(
                Replace(Trim("room_unit_label"), Value(" "), Value("")),
                Value("-"),
                Value(""),
            )
        )
    )
    normalized.filter(
        normalized_room__in=["owner", "ownerroom", "ownerunit"]
    ).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0071_record_aaron_july_cleaning_utility_credit")]

    operations = [migrations.RunPython(remove_owner_snapshots, noop_reverse)]
