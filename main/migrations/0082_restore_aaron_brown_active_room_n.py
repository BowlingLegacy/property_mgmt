from decimal import Decimal

from django.db import migrations
from django.db.models import Q
from django.utils import timezone


RESTORE_NOTE = "2026-10-07: Move-out canceled. Tenancy restored to active in Room N."


def restore_aaron_brown(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    CurrentResidentRosterEntry = apps.get_model("main", "CurrentResidentRosterEntry")
    PropertyRoomRent = apps.get_model("main", "PropertyRoomRent")

    residents = (
        HousingApplication.objects
        .filter(
            Q(full_name__iexact="Aaron Brown")
            | Q(full_name__iexact="Aaron Brian Brown")
        )
        .order_by("-id")
    )

    # Restore only the most recent resident file if older duplicate records exist.
    for resident in residents[:1]:
        if not resident.property_id:
            continue

        resident.tenancy_status = "active"
        resident.application_folder = "active"
        resident.application_folder_updated_at = timezone.now()
        resident.space_type = "Room"
        resident.space_label = "N"
        resident.move_out_date = None
        resident.former_tenant_archived_at = None
        resident.tenancy_end_reason = ""
        resident.tenancy_archive_notes = ""

        existing_notes = (resident.additional_notes or "").strip()
        if RESTORE_NOTE not in existing_notes:
            resident.additional_notes = f"{existing_notes}\n\n{RESTORE_NOTE}".strip()

        room_setting = (
            PropertyRoomRent.objects
            .filter(property_id=resident.property_id)
            .filter(Q(room_unit_label__iexact="N") | Q(room_unit_label__iexact="Room N"))
            .order_by("id")
            .first()
        )
        if room_setting:
            if room_setting.monthly_rent and room_setting.monthly_rent > Decimal("0.00"):
                resident.monthly_rent = room_setting.monthly_rent
            if room_setting.utility_monthly and room_setting.utility_monthly > Decimal("0.00"):
                resident.utility_monthly = room_setting.utility_monthly

        resident.save(update_fields=[
            "tenancy_status",
            "application_folder",
            "application_folder_updated_at",
            "space_type",
            "space_label",
            "move_out_date",
            "former_tenant_archived_at",
            "tenancy_end_reason",
            "tenancy_archive_notes",
            "additional_notes",
            "monthly_rent",
            "utility_monthly",
        ])

        if resident.user_id:
            User = apps.get_model("main", "User")
            User.objects.filter(id=resident.user_id).update(is_active=True)

        aaron_roster_entries = CurrentResidentRosterEntry.objects.filter(
            property_id=resident.property_id,
            first_name__iexact="Aaron",
            last_name__iexact="Brown",
        )
        primary_roster_entry = (
            aaron_roster_entries
            .filter(Q(room_unit_label__iexact="N") | Q(room_unit_label__iexact="Room N"))
            .order_by("-is_active", "-id")
            .first()
            or aaron_roster_entries.order_by("-is_active", "-id").first()
        )
        aaron_roster_entries.update(is_active=False)

        if primary_roster_entry:
            primary_roster_entry.room_unit_label = "N"
            primary_roster_entry.is_active = True
            if resident.email:
                primary_roster_entry.email = resident.email
            if resident.phone:
                primary_roster_entry.phone = resident.phone
            primary_roster_entry.save(update_fields=[
                "room_unit_label", "is_active", "email", "phone",
            ])
        else:
            CurrentResidentRosterEntry.objects.create(
                property_id=resident.property_id,
                first_name="Aaron",
                last_name="Brown",
                email=resident.email or "",
                phone=resident.phone or "",
                room_unit_label="N",
                is_active=True,
            )


class Migration(migrations.Migration):
    dependencies = [("main", "0081_add_belmont_family_history")]

    operations = [migrations.RunPython(restore_aaron_brown, migrations.RunPython.noop)]
