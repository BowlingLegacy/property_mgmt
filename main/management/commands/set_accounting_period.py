from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Sum
from django.utils import timezone

from main.models import AccountingPeriod, AccountingReceipt, FinancialEntry, Property


class Command(BaseCommand):
    help = "Open or close one property's accounting period."

    def add_arguments(self, parser):
        parser.add_argument("--property-name", required=True)
        parser.add_argument("--month", required=True, help="Accounting month in YYYY-MM format.")
        parser.add_argument("--status", choices=["open", "closed"], required=True)
        parser.add_argument("--notes", default="")
        parser.add_argument("--allow-open-receipts", action="store_true")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        property_name = options["property_name"]
        month_value = options["month"]
        status = options["status"]

        try:
            month_start = datetime.strptime(month_value, "%Y-%m").date()
        except ValueError as exc:
            raise CommandError("Use --month in YYYY-MM format, for example 2026-05.") from exc

        property_obj = Property.objects.filter(name=property_name).first()
        if not property_obj:
            raise CommandError(f"No property found named {property_name!r}.")

        entries = FinancialEntry.objects.filter(
            property_name=property_obj.name,
            year=month_start.year,
            month=month_start.month,
        )
        receipt_queue = AccountingReceipt.objects.filter(
            property=property_obj,
            receipt_date__year=month_start.year,
            receipt_date__month=month_start.month,
            status="needs_review",
        )

        totals = entries.values("entry_type").annotate(total=Sum("amount"), count=Count("id")).order_by("entry_type")

        self.stdout.write("Accounting period update preview")
        self.stdout.write("================================")
        self.stdout.write(f"Property: {property_obj.name}")
        self.stdout.write(f"Month: {month_start.strftime('%B %Y')}")
        self.stdout.write(f"Requested status: {status}")
        self.stdout.write("")
        self.stdout.write("Ledger totals")
        self.stdout.write("-------------")
        if totals:
            for row in totals:
                self.stdout.write(f"{row['entry_type']}: ${row['total'] or 0:.2f} across {row['count']} entries")
        else:
            self.stdout.write("No ledger entries for this month.")

        open_count = receipt_queue.count()
        self.stdout.write("")
        self.stdout.write(f"Receipts still needing review: {open_count}")

        if status == "closed" and open_count and not options["allow_open_receipts"]:
            raise CommandError("Review or ignore the open receipts first, or rerun with --allow-open-receipts.")

        if not options["confirm"]:
            self.stdout.write("")
            self.stdout.write("Dry run only. No accounting period was changed.")
            self.stdout.write("Run again with --confirm to save this status.")
            return

        period, _ = AccountingPeriod.objects.get_or_create(
            property=property_obj,
            month=month_start.month,
            year=month_start.year,
        )
        period.status = status
        period.notes = options["notes"]

        if status == "closed":
            period.closed_at = timezone.now()
            period.closed_by = None
        else:
            period.closed_at = None
            period.closed_by = None

        period.save(update_fields=["status", "notes", "closed_at", "closed_by", "updated_at"])

        self.stdout.write("")
        self.stdout.write(f"Accounting period is now {status}.")
