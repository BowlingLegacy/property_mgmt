from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from main.models import Payment, Property


def parse_month(value):
    try:
        return datetime.strptime(value, "%Y-%m").date().replace(day=1)
    except ValueError as exc:
        raise CommandError(f"Invalid month '{value}'. Use YYYY-MM.") from exc


class Command(BaseCommand):
    help = "Set received_at day for migrated historical payments in a month range."

    def add_arguments(self, parser):
        parser.add_argument("--property-name", required=True)
        parser.add_argument("--from-month", required=True, help="YYYY-MM")
        parser.add_argument("--to-month", required=True, help="YYYY-MM")
        parser.add_argument("--day", type=int, default=3)
        parser.add_argument("--description-contains", default="Historical")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        property_name = options["property_name"]
        from_month = parse_month(options["from_month"])
        to_month = parse_month(options["to_month"])
        day = options["day"]

        if day < 1 or day > 28:
            raise CommandError("Day must be between 1 and 28 so every month can be updated safely.")
        if from_month > to_month:
            raise CommandError("--from-month must be before or equal to --to-month.")

        property_obj = Property.objects.filter(name=property_name).first()
        if not property_obj:
            raise CommandError(f"No property found named '{property_name}'.")

        payments = (
            Payment.objects
            .select_related("application")
            .filter(
                application__property=property_obj,
                status="completed",
                service_month__gte=from_month,
                service_month__lte=to_month,
            )
            .order_by("service_month", "application__space_label", "application__full_name", "payment_type", "id")
        )
        description_contains = (options["description_contains"] or "").strip()
        if description_contains:
            payments = payments.filter(description__icontains=description_contains)

        selected = list(payments)
        self.stdout.write("Historical payment received date update")
        self.stdout.write("=======================================")
        self.stdout.write(f"Property: {property_obj.name}")
        self.stdout.write(f"Months: {from_month:%B %Y} through {to_month:%B %Y}")
        self.stdout.write(f"New received day: {day}")
        self.stdout.write(f"Payments selected: {len(selected)}")

        for payment in selected:
            new_date = payment.service_month.replace(day=day)
            new_received_at = timezone.make_aware(datetime.combine(new_date, datetime.min.time()))
            old_value = payment.received_at or payment.created_at
            self.stdout.write(
                f"UPDATE | payment {payment.id} | {payment.application.space_label or '-'} | "
                f"{payment.application.full_name} | {payment.payment_type} | ${payment.amount} | "
                f"{old_value:%Y-%m-%d} -> {new_received_at:%Y-%m-%d}"
            )

        if not options["confirm"]:
            self.stdout.write("Dry run only. No payment dates were changed.")
            self.stdout.write("Run again with --confirm to update these records.")
            return

        for payment in selected:
            new_date = payment.service_month.replace(day=day)
            payment.received_at = timezone.make_aware(datetime.combine(new_date, datetime.min.time()))
            payment.save(update_fields=["received_at"])

        self.stdout.write(self.style.SUCCESS("Historical payment received date update complete."))
        self.stdout.write(f"Payments updated: {len(selected)}")
