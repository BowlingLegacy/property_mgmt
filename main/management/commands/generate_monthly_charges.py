from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import HousingApplication, MonthlyCharge


LATE_FEE_AMOUNT = Decimal("25.00")


class Command(BaseCommand):
    help = "Generate monthly charges"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview charges without saving"
        )
        parser.add_argument(
            "--resident-id",
            type=int,
            help="Generate charges for one resident only"
        )
    def handle(self, *args, **options):

        dry_run = options["dry_run"]

        today = timezone.localdate()

        month = today.month
        year = today.year

        applications = HousingApplication.objects.all()

        created_count = 0

        for application in applications:

            if application.monthly_rent <= 0:
                continue

            existing = MonthlyCharge.objects.filter(
                application=application,
                month=month,
                year=year,
            ).exists()

            if existing:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping existing charge: {application.full_name}"
                    )
                )
                continue

            rent_charge = application.monthly_rent
            utility_charge = application.utility_monthly

            late_fee = Decimal("0.00")

            if today.day > 5 and application.balance > 0:
                late_fee = LATE_FEE_AMOUNT

            total = rent_charge + utility_charge + late_fee

            self.stdout.write(
                self.style.SUCCESS(
                    f"""
Resident: {application.full_name}
Rent: ${rent_charge}
Utilities: ${utility_charge}
Late Fee: ${late_fee}
Total: ${total}
"""
                )
            )

            if not dry_run:

                MonthlyCharge.objects.create(
                    application=application,
                    month=month,
                    year=year,
                    rent_charge=rent_charge,
                    utility_charge=utility_charge,
                    late_fee=late_fee,
                )

                application.balance += rent_charge + late_fee
                application.utility_balance += utility_charge
                application.save()

            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nProcessed {created_count} monthly charges."
            )
        )
