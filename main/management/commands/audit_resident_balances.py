from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from main.models import HousingApplication, Property, ResidentBalanceEntry


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError) as exc:
        raise CommandError(f"Invalid money value: {value}") from exc


def has_fractional_dollar(value):
    value = Decimal(value or "0.00")
    return value != value.quantize(Decimal("1"))


class Command(BaseCommand):
    help = "Audit or correct stored resident balance fields without changing payment history."

    def add_arguments(self, parser):
        parser.add_argument("--property-name", required=True)
        parser.add_argument("--resident-name", default="")
        parser.add_argument("--room", default="")
        parser.add_argument("--rent-balance", default=None)
        parser.add_argument("--utility-balance", default=None)
        parser.add_argument("--deposit-paid", default=None)
        parser.add_argument("--only-suspicious", action="store_true")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        property_obj = Property.objects.filter(name=options["property_name"]).first()
        if not property_obj:
            raise CommandError(f"No property found named '{options['property_name']}'.")

        queryset = HousingApplication.objects.filter(property=property_obj).order_by("space_label", "full_name", "id")
        if options["resident_name"]:
            queryset = queryset.filter(full_name__icontains=options["resident_name"])
        if options["room"]:
            queryset = queryset.filter(space_label__iexact=options["room"])

        residents = list(queryset)
        if not residents:
            raise CommandError("No matching resident files found.")

        correction_requested = any(options[name] is not None for name in ["rent_balance", "utility_balance", "deposit_paid"])
        if correction_requested and len(residents) != 1:
            raise CommandError("Balance correction requires exactly one matching resident. Add --resident-name or --room.")

        self.stdout.write("Resident balance audit")
        self.stdout.write("======================")
        self.stdout.write(f"Property: {property_obj.name}")

        selected = []
        for resident in residents:
            ledger_count = ResidentBalanceEntry.objects.filter(application=resident).count()
            suspicious = (
                has_fractional_dollar(resident.balance)
                or has_fractional_dollar(resident.utility_balance)
                or has_fractional_dollar(resident.deposit_paid)
            )
            if options["only_suspicious"] and not suspicious:
                continue
            selected.append(resident)
            flag = "SUSPICIOUS" if suspicious else "OK"
            self.stdout.write(
                f"{flag} | app {resident.id} | room {resident.space_label or '-'} | {resident.full_name} | "
                f"rent_balance=${resident.balance} | utility_balance=${resident.utility_balance} | "
                f"deposit_paid=${resident.deposit_paid} | balance_entries={ledger_count}"
            )

        if not selected:
            self.stdout.write("No matching resident balances found for the selected filters.")
            return

        if not correction_requested:
            self.stdout.write("Audit only. No balances were changed.")
            return

        resident = selected[0]
        updates = {}
        if options["rent_balance"] is not None:
            updates["balance"] = money(options["rent_balance"])
        if options["utility_balance"] is not None:
            updates["utility_balance"] = money(options["utility_balance"])
        if options["deposit_paid"] is not None:
            updates["deposit_paid"] = money(options["deposit_paid"])

        self.stdout.write("")
        self.stdout.write(f"Correction target: app {resident.id} | {resident.full_name} | room {resident.space_label or '-'}")
        for field, new_value in updates.items():
            self.stdout.write(f"{field}: ${getattr(resident, field)} -> ${new_value}")

        if not options["confirm"]:
            self.stdout.write("Dry run only. Add --confirm to save this correction.")
            return

        for field, new_value in updates.items():
            setattr(resident, field, new_value)
        resident.save(update_fields=list(updates.keys()))
        self.stdout.write(self.style.SUCCESS("Resident balance correction complete."))
