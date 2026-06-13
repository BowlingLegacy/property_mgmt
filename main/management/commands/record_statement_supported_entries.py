from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from main.models import ExpenseCategory, FinancialEntry, FinancialUpload, Property


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError) as exc:
        raise CommandError(f"Invalid money value: {value}") from exc


class Command(BaseCommand):
    help = "Create statement-supported ledger entries for bank auto-pay items with no invoice."

    def add_arguments(self, parser):
        parser.add_argument("--property-name", required=True)
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--months", required=True, help="Comma-separated month numbers, for example 5,6.")
        parser.add_argument("--amount", required=True)
        parser.add_argument("--entry-type", default="debt_service", choices=[
            "income",
            "operating_expense",
            "debt_service",
            "capital_expense",
            "other",
        ])
        parser.add_argument("--category", required=True)
        parser.add_argument("--vendor", default="")
        parser.add_argument("--day", type=int, default=1)
        parser.add_argument("--description", default="")
        parser.add_argument("--source-name", default="Statement Supported Ledger Entries")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        property_obj = Property.objects.filter(name=options["property_name"].strip()).first()
        if not property_obj:
            raise CommandError(f"No property found named '{options['property_name']}'.")

        amount = money(options["amount"])
        if amount <= 0:
            raise CommandError("Amount must be greater than zero.")

        months = []
        for raw_month in str(options["months"]).split(","):
            try:
                month = int(raw_month.strip())
            except ValueError as exc:
                raise CommandError(f"Invalid month: {raw_month}") from exc
            if month < 1 or month > 12:
                raise CommandError(f"Month must be 1 through 12: {month}")
            months.append(month)

        if not months:
            raise CommandError("At least one month is required.")

        entry_type = options["entry_type"]
        category = options["category"].strip()
        vendor = options["vendor"].strip()
        day = options["day"]
        description = options["description"].strip()

        entries_to_create = []
        duplicate_entries = []
        for month in months:
            try:
                entry_date = date(options["year"], month, day)
            except ValueError as exc:
                raise CommandError(f"Invalid date for {options['year']}-{month:02d}-{day:02d}") from exc

            entry_description = description
            if vendor and vendor.lower() not in entry_description.lower():
                entry_description = f"{vendor} - {entry_description}" if entry_description else vendor
            if not entry_description:
                entry_description = "Bank-statement supported payment; no invoice issued."

            duplicate = FinancialEntry.objects.filter(
                property_name=property_obj.name,
                entry_date=entry_date,
                entry_type=entry_type,
                category=category,
                amount=amount,
                description=entry_description,
            ).first()

            if duplicate:
                duplicate_entries.append(duplicate)
            else:
                entries_to_create.append({
                    "entry_date": entry_date,
                    "month": month,
                    "description": entry_description,
                })

        self.stdout.write("Statement-supported ledger entry preview")
        self.stdout.write("========================================")
        self.stdout.write(f"Property: {property_obj.name}")
        self.stdout.write(f"Type: {entry_type}")
        self.stdout.write(f"Category: {category}")
        self.stdout.write(f"Amount: ${amount}")
        self.stdout.write(f"Rows to create: {len(entries_to_create)}")

        for entry in entries_to_create:
            self.stdout.write(
                f"CREATE | {entry['entry_date']} | {entry_type} | {category} | "
                f"${amount} | {entry['description']}"
            )

        for duplicate in duplicate_entries:
            self.stdout.write(
                f"SKIP duplicate | entry {duplicate.id} | {duplicate.entry_date} | "
                f"{duplicate.entry_type} | {duplicate.category} | ${duplicate.amount}"
            )

        if not options["confirm"]:
            self.stdout.write(self.style.WARNING("Dry run only. No entries were created."))
            self.stdout.write("Run again with --confirm to create these ledger entries.")
            return

        if entry_type != "income":
            ExpenseCategory.objects.get_or_create(
                name=category,
                defaults={"entry_type": entry_type, "created_by": None},
            )

        source_slug = slugify(f"{property_obj.name}-{options['source_name']}-{options['year']}") or "statement-supported"
        file_body = (
            "statement_supported_entries\n"
            f"property,{property_obj.name}\n"
            f"created_at,{timezone.now().isoformat()}\n"
            "documentation,bank statement supported; no invoice issued\n"
        )

        with transaction.atomic():
            upload = FinancialUpload.objects.create(
                property=property_obj,
                ledger_scope="property",
                name=options["source_name"],
                file=ContentFile(file_body.encode("utf-8"), name=f"{source_slug}.csv"),
                notes="Bank-statement supported ledger source for recurring payments with no invoice.",
                parsed_at=timezone.now(),
            )

            for row_number, entry in enumerate(entries_to_create, start=1):
                FinancialEntry.objects.create(
                    upload=upload,
                    ledger_scope="property",
                    property_name=property_obj.name,
                    sheet_name="Statement Supported",
                    row_number=row_number,
                    entry_date=entry["entry_date"],
                    month=entry["month"],
                    year=options["year"],
                    entry_type=entry_type,
                    category=category,
                    description=entry["description"],
                    amount=amount,
                )

        self.stdout.write(self.style.SUCCESS(f"Created {len(entries_to_create)} statement-supported ledger entries."))
