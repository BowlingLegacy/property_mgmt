from django.db import migrations
from django.db.models import Q


def set_roster_room(CurrentResidentRosterEntry, resident, first_name, last_name, room):
    entries = CurrentResidentRosterEntry.objects.filter(
        property_id=resident.property_id,
        first_name__iexact=first_name,
        last_name__iregex=last_name,
    )
    target = entries.filter(
        Q(room_unit_label__iexact=room) | Q(room_unit_label__iexact=f"Room {room}")
    ).order_by("-id").first()
    if target:
        target.room_unit_label = room
        target.is_active = True
        target.save(update_fields=["room_unit_label", "is_active"])
        entries.exclude(id=target.id).update(is_active=False)
        return

    source = entries.order_by("-id").first()
    if source:
        source.room_unit_label = room
        source.is_active = True
        source.save(update_fields=["room_unit_label", "is_active"])


def correct_rooms_i_and_j_occupancy(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    CurrentResidentRosterEntry = apps.get_model("main", "CurrentResidentRosterEntry")

    mike = (
        HousingApplication.objects
        .filter(full_name__iregex=r"^Mike\s+Dudl(e)?y$", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if mike:
        mike.space_type = "Room"
        mike.space_label = "J"
        mike.tenancy_status = "active"
        mike.application_folder = "active"
        mike.save(update_fields=["space_type", "space_label", "tenancy_status", "application_folder"])
        set_roster_room(CurrentResidentRosterEntry, mike, "Mike", r"Dudl(e)?y", "J")

    mark = (
        HousingApplication.objects
        .filter(full_name__iexact="Mark Moore", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if mark:
        mark.space_type = "Room"
        mark.space_label = "I"
        mark.tenancy_status = "active"
        mark.application_folder = "active"
        mark.save(update_fields=["space_type", "space_label", "tenancy_status", "application_folder"])
        set_roster_room(CurrentResidentRosterEntry, mark, "Mark", r"Moore", "I")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0062_correct_room_h_current_occupant")]

    operations = [migrations.RunPython(correct_rooms_i_and_j_occupancy, noop_reverse)]
