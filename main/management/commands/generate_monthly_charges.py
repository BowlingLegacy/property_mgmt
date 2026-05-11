from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import HousingApplication, Payment


LATE_FEE_AMOUNT = Decimal("25.00")


class Command(BaseCommand):
    help = "Generate monthly rent, utilities, and late fees"

    def handle(self, *args, **options):

        today = timezone.localdate()

        current_month = today.month
        current_year = today.year

        applications = HousingApplication.objects.all()

        created_rent = 0
        created_utilities = 0
        created_late_fees = 0

        for application in applications:

            # Skip incomplete resident files
            if not application.monthly_rent:
                continue

            # -----------------------------------
            # RENT CHARGE
            # -----------------------------------

            existing_rent = Payment.objects.filter(
                application=application,
                payment_type="rent",
                description__icontains=f"{today.strftime('%B')} {current_year}",
            ).exists()

            if not existing_rent:

                application.balance += application.monthly_rent

                Payment.objects.create(
                    application=application,
                    payment_type="rent",
                    description=f"{today.strftime('%B')} {current_year} Monthly Rent Charge",
                    amount=application.monthly_rent,
                    status="completed",
                )

                created_rent += 1

            # -----------------------------------
            # UTILITY CHARGE
            # -----------------------------------

            existing_utility = Payment.objects.filter(
                application=application,
                payment_type="utility",
                description__icontains=f"{today.strftime('%B')} {current_year}",
            ).exists()

            if not existing_utility:

                application.utility_balance += application.utility_monthly

                Payment.objects.create(
                    application=application,
                    payment_type="utility",
                    description=f"{today.strftime('%B')} {current_year} Utility Charge",
                    amount=application.utility_monthly,
                    status="completed",
                )

                created_utilities += 1

            # -----------------------------------
            # LATE FEE
            # -----------------------------------

            if today.day > 5 and application.balance > 0:

                existing_late_fee = Payment.objects.filter(
                    application=application,
                    payment_type="late_fee",
                    description__icontains=f"{today.strftime('%B')} {current_year}",
                ).exists()

                if not existing_late_fee:

                    application.balance += LATE_FEE_AMOUNT

                    Payment.objects.create(
                        application=application,
                        payment_type="late_fee",
                        description=f"{today.strftime('%B')} {current_year} Late Fee",
                        amount=LATE_FEE_AMOUNT,
                        status="completed",
                    )

                    created_late_fees += 1

            application.save()

        self.stdout.write(self.style.SUCCESS(
            f"""
Monthly charges generated successfully.

Rent Charges Created: {created_rent}
Utility Charges Created: {created_utilities}
Late Fees Created: {created_late_fees}
"""
        ))
