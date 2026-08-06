from datetime import date

from django.db import migrations
from django.db.models import Q
from django.utils import timezone


def activate_roster_entry(CurrentResidentRosterEntry, resident, first_name, last_name, room):
    entries = CurrentResidentRosterEntry.objects.filter(
        property_id=resident.property_id,
        first_name__iexact=first_name,
        last_name__iexact=last_name,
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


def correct_room_h_current_occupant(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    CurrentResidentRosterEntry = apps.get_model("main", "CurrentResidentRosterEntry")

    for felicia in HousingApplication.objects.filter(full_name__iexact="Felicia Valdez"):
        felicia.tenancy_status = "former"
        felicia.application_folder = "archived"
        if not felicia.move_out_date or felicia.move_out_date > date(2026, 6, 30):
            felicia.move_out_date = date(2026, 6, 30)
        felicia.former_tenant_archived_at = timezone.now()
        felicia.tenancy_end_reason = "Moved out during June 2026"
        felicia.save(update_fields=[
            "tenancy_status", "application_folder", "move_out_date",
            "former_tenant_archived_at", "tenancy_end_reason",
        ])
        CurrentResidentRosterEntry.objects.filter(
            property_id=felicia.property_id,
            first_name__iexact="Felicia",
            last_name__iexact="Valdez",
        ).update(is_active=False)

    arjen = (
        HousingApplication.objects
        .filter(full_name__iregex=r"^Arjen\s+Pomalaza$", property_id__isnull=False)
        .order_by("-id")
        .first()
    )
    if not arjen:
        return

    arjen.space_type = "Room"
    arjen.space_label = "H"
    arjen.tenancy_status = "active"
    arjen.application_folder = "active"
    update_fields = ["space_type", "space_label", "tenancy_status", "application_folder"]
    if not arjen.lease_start_date:
        arjen.lease_start_date = date(2026, 7, 1)
        update_fields.append("lease_start_date")
    arjen.save(update_fields=update_fields)

    activate_roster_entry(CurrentResidentRosterEntry, arjen, "Arjen", "Pomalaza", "H")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0061_correct_chris_honey_rent")]

    operations = [migrations.RunPython(correct_room_h_current_occupant, noop_reverse)]
