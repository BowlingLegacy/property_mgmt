from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from main.models import HousingApplication, Property


def clean_match_value(value):
    return " ".join(str(value or "").strip().lower().split())


def normalized_room_label(room_unit_label):
    label = clean_match_value(room_unit_label)
    prefixes = ["room", "unit", "space", "apt", "apartment"]
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            prefix_value = f"{prefix} "
            if label.startswith(prefix_value):
                label = label[len(prefix_value):].strip()
                changed = True
                break
            if label.startswith(prefix) and len(label) > len(prefix):
                label = label[len(prefix):].lstrip(" -#").strip()
                changed = True
                break
    return label


def canonical_room_label(room_unit_label):
    clean_label = normalized_room_label(room_unit_label)
    if not clean_label:
        return str(room_unit_label or "").strip()
    if len(clean_label) == 1:
        return clean_label.upper()
    return clean_label.upper() if clean_label.isalpha() else clean_label


def is_room_placeholder(application):
    room_label = canonical_room_label(application.space_label)
    if not room_label:
        return False

    resident_name = clean_match_value(application.full_name)
    if not resident_name:
        return True

    room_name = room_label.lower()
    return resident_name in {room_name, f"room {room_name}"}


class Command(BaseCommand):
    help = "Preview or archive no-login Room X placeholder resident files when a linked resident exists in the same unit."

    def add_arguments(self, parser):
        parser.add_argument("--property-name", required=True)
        parser.add_argument("--room", default="", help="Optional unit label such as M or Room M.")
        parser.add_argument(
            "--include-named-no-login",
            action="store_true",
            help="Also select named no-login records in units that already have a linked resident.",
        )
        parser.add_argument(
            "--include-no-unit-no-login",
            action="store_true",
            help="Also select no-login active records with no unit assignment.",
        )
        parser.add_argument("--delete", action="store_true", help="Hard-delete placeholders instead of archiving them.")
        parser.add_argument("--confirm", action="store_true", help="Actually archive/delete selected placeholder records.")

    def handle(self, *args, **options):
        property_obj = Property.objects.filter(name=options["property_name"].strip()).first()
        if not property_obj:
            raise CommandError(f"No property found named '{options['property_name']}'.")

        applications = list(
            HousingApplication.objects
            .select_related("property", "user")
            .filter(property=property_obj, tenancy_status="active")
            .order_by("space_label", "full_name", "id")
        )

        target_room = normalized_room_label(options["room"]) if options["room"] else ""
        if target_room:
            applications = [
                application
                for application in applications
                if normalized_room_label(application.space_label) == target_room
            ]

        linked_by_room = {}
        for application in applications:
            room_key = normalized_room_label(application.space_label)
            if not room_key or not application.user_id:
                continue
            linked_by_room.setdefault(room_key, []).append(application)

        candidates = []
        for application in applications:
            room_key = normalized_room_label(application.space_label)
            if not application.user_id and not room_key and options["include_no_unit_no_login"]:
                candidates.append((application, []))
                continue
            if application.user_id or room_key not in linked_by_room:
                continue
            if is_room_placeholder(application) or options["include_named_no_login"]:
                candidates.append((application, linked_by_room[room_key]))

        action = "DELETE" if options["delete"] else "ARCHIVE"
        self.stdout.write("Room placeholder resident cleanup preview")
        self.stdout.write("========================================")
        self.stdout.write(f"Property: {property_obj.name}")
        if target_room:
            self.stdout.write(f"Room filter: {canonical_room_label(target_room)}")
        self.stdout.write(f"Action: {action}")
        self.stdout.write(f"Placeholders selected: {len(candidates)}")

        for application, linked_residents in candidates:
            linked_names = ", ".join(f"app {resident.id} {resident.full_name}" for resident in linked_residents) or "-"
            self.stdout.write(
                f"{action} | app {application.id} | Room {canonical_room_label(application.space_label)} | "
                f"{application.full_name or '-'} | linked resident(s): {linked_names}"
            )

        if not candidates:
            self.stdout.write("No room placeholder resident files matched the cleanup rules.")
            return

        if not options["confirm"]:
            self.stdout.write(self.style.WARNING("Dry run only. No records were changed."))
            self.stdout.write("Run again with --confirm to apply this cleanup.")
            return

        now = timezone.now()
        with transaction.atomic():
            for application, _linked_residents in candidates:
                if options["delete"]:
                    application.delete()
                    continue

                if not normalized_room_label(application.space_label):
                    note = "Archived no-login record with no unit assignment because it was not an active tenant file."
                    reason = "Non-tenant no-unit record"
                elif is_room_placeholder(application):
                    note = "Archived duplicate no-login room placeholder after linked resident file was found for the same unit."
                    reason = "Duplicate room placeholder"
                else:
                    note = "Archived no-login resident record after linked resident file was found for the same unit."
                    reason = "Duplicate no-login resident record"
                existing_notes = str(application.tenancy_archive_notes or "").strip()
                application.tenancy_status = "former"
                application.application_folder = "archived"
                application.application_folder_updated_at = now
                application.former_tenant_archived_at = now
                application.tenancy_end_reason = reason
                application.tenancy_archive_notes = f"{existing_notes}\n{note}".strip()
                application.save(update_fields=[
                    "tenancy_status",
                    "application_folder",
                    "application_folder_updated_at",
                    "former_tenant_archived_at",
                    "tenancy_end_reason",
                    "tenancy_archive_notes",
                ])

        self.stdout.write(self.style.SUCCESS("Room placeholder resident cleanup complete."))
