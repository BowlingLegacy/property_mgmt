from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from main.models import HousingApplication, ResidentBalanceEntry


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError) as exc:
        raise CommandError(f"Invalid money value: {value}") from exc


def month_value(value):
    if not value:
        return None
    try:
        year, month = [int(part) for part in value.split("-", 1)]
    except ValueError as exc:
        raise CommandError("Use YYYY-MM for --service-month.") from exc
    from datetime import date
    return date(year, month, 1)


class Command(BaseCommand):
    help = "List, add, update, or delete resident balance ledger entries."

    def add_arguments(self, parser):
        parser.add_argument("--property-name", required=True)
        parser.add_argument("--resident-name", required=True)
        parser.add_argument("--list", action="store_true")
        parser.add_argument("--add", action="store_true")
        parser.add_argument("--update-id", type=int)
        parser.add_argument("--delete-id", type=int)
        parser.add_argument("--entry-kind", choices=["charge", "credit"])
        parser.add_argument("--balance-type", choices=["rent", "utility"])
        parser.add_argument("--amount")
        parser.add_argument("--service-month", help="YYYY-MM")
        parser.add_argument("--description", default="")
        parser.add_argument("--notes", default="")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        residents = list(
            HousingApplication.objects
            .filter(property__name=options["property_name"], full_name__icontains=options["resident_name"])
            .order_by("space_label", "full_name", "id")
        )
        if not residents:
            raise CommandError("No matching resident found.")
        if len(residents) != 1:
            self.stdout.write("Multiple residents matched:")
            for resident in residents:
                self.stdout.write(f"app {resident.id} | room {resident.space_label or '-'} | {resident.full_name}")
            raise CommandError("Use a more specific --resident-name.")

        resident = residents[0]
        self.stdout.write(f"Resident: app {resident.id} | room {resident.space_label or '-'} | {resident.full_name}")

        if options["list"] or not any([options["add"], options["update_id"], options["delete_id"]]):
            self.list_entries(resident)
            if not any([options["add"], options["update_id"], options["delete_id"]]):
                return

        if options["delete_id"]:
            entry = self.get_entry(resident, options["delete_id"])
            self.stdout.write(f"DELETE | {self.entry_line(entry)}")
            if not options["confirm"]:
                self.stdout.write("Dry run only. Add --confirm to delete this entry.")
                return
            entry.delete()
            self.stdout.write(self.style.SUCCESS("Entry deleted."))
            return

        if options["update_id"]:
            entry = self.get_entry(resident, options["update_id"])
            changes = {}
            if options["entry_kind"]:
                changes["entry_kind"] = options["entry_kind"]
            if options["balance_type"]:
                changes["balance_type"] = options["balance_type"]
            if options["amount"] is not None:
                changes["amount"] = money(options["amount"])
            if options["service_month"] is not None:
                changes["service_month"] = month_value(options["service_month"])
            if options["description"]:
                changes["description"] = options["description"]
            if options["notes"]:
                changes["notes"] = options["notes"]

            if not changes:
                raise CommandError("No update fields provided.")

            self.stdout.write(f"UPDATE | {self.entry_line(entry)}")
            for field, value in changes.items():
                self.stdout.write(f"  {field}: {getattr(entry, field)} -> {value}")
            if not options["confirm"]:
                self.stdout.write("Dry run only. Add --confirm to update this entry.")
                return
            for field, value in changes.items():
                setattr(entry, field, value)
            entry.save(update_fields=list(changes.keys()))
            self.stdout.write(self.style.SUCCESS("Entry updated."))
            return

        if options["add"]:
            required = ["entry_kind", "balance_type", "amount", "service_month", "description"]
            missing = [name for name in required if not options[name]]
            if missing:
                raise CommandError(f"Missing required option(s) for --add: {', '.join('--' + name.replace('_', '-') for name in missing)}")
            service_month = month_value(options["service_month"])
            amount = money(options["amount"])
            self.stdout.write(
                f"ADD | {options['entry_kind']} | {options['balance_type']} | ${amount} | "
                f"{service_month:%B %Y} | {options['description']}"
            )
            if not options["confirm"]:
                self.stdout.write("Dry run only. Add --confirm to create this entry.")
                return
            ResidentBalanceEntry.objects.create(
                application=resident,
                entry_kind=options["entry_kind"],
                balance_type=options["balance_type"],
                amount=amount,
                service_month=service_month,
                description=options["description"],
                notes=options["notes"],
            )
            self.stdout.write(self.style.SUCCESS("Entry created."))

    def get_entry(self, resident, entry_id):
        entry = ResidentBalanceEntry.objects.filter(application=resident, id=entry_id).first()
        if not entry:
            raise CommandError(f"No balance entry {entry_id} found for {resident.full_name}.")
        return entry

    def list_entries(self, resident):
        entries = ResidentBalanceEntry.objects.filter(application=resident).order_by("created_at", "id")
        if not entries:
            self.stdout.write("No balance entries found.")
            return
        self.stdout.write("Balance entries:")
        for entry in entries:
            self.stdout.write(self.entry_line(entry))

    def entry_line(self, entry):
        month = entry.service_month.strftime("%Y-%m") if entry.service_month else "-"
        return (
            f"id {entry.id} | {entry.entry_kind} | {entry.balance_type} | ${entry.amount} | "
            f"{month} | {entry.description} | {entry.notes or '-'}"
        )
