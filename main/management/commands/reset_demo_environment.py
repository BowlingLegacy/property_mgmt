from datetime import date, datetime
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from main.models import (
    BlogPost,
    CurrentResidentRosterEntry,
    ExpenseCategory,
    FinancialEntry,
    FinancialUpload,
    HousingApplication,
    Payment,
    Property,
    PropertyOwnerIntake,
    PropertyRoomRent,
    ResidentMessage,
    User,
)


class Command(BaseCommand):
    help = "Reset the isolated demo database and seed it with temporary sample property data."

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true", help="Required to perform the reset.")

    def handle(self, *args, **options):
        if not getattr(settings, "DEMO_MODE", False):
            raise CommandError("Refusing to reset data because DEMO_MODE is not enabled.")

        if not options["confirm"]:
            raise CommandError("Run again with --confirm to reset and reseed the demo environment.")

        with transaction.atomic():
            self.delete_main_app_data()
            self.seed_demo_data()

        self.stdout.write(self.style.SUCCESS("Demo environment reset complete."))
        self.stdout.write("Demo entry URL: /demo/")
        self.stdout.write(f"Demo admin username: {settings.DEMO_ADMIN_USERNAME}")

    def delete_main_app_data(self):
        for model in reversed(list(apps.get_app_config("main").get_models())):
            model.objects.all().delete()

    def seed_demo_data(self):
        admin = User.objects.create_superuser(
            username=settings.DEMO_ADMIN_USERNAME,
            email="demo-admin@example.com",
            password="DemoPass123!",
            role="admin",
        )
        owner = User.objects.create_user(
            username="demo-owner",
            email="owner@example.com",
            password="DemoPass123!",
            role="property_owner",
            first_name="Olivia",
            last_name="Owner",
        )
        landlord = User.objects.create_user(
            username="demo-landlord",
            email="landlord@example.com",
            password="DemoPass123!",
            role="landlord",
            first_name="Larry",
            last_name="Landlord",
            is_staff=True,
        )

        property_obj = Property.objects.create(
            name="Demo Ridge Apartments",
            address="100 Sample Way, Medford, OR",
            owner_email=owner.email,
            landlord_email=landlord.email,
            description="Demo multifamily property used for product tours and temporary trial data.",
            availability_status="available",
            availability_message="Demo units available for testing",
            rent_amount=Decimal("1250.00"),
            deposit_amount=Decimal("900.00"),
            utilities_cost="Resident electric, shared water billed monthly",
            charges_application_fee=True,
            application_fee_amount=Decimal("45.00"),
            requires_background_check=True,
            background_check_fee_amount=Decimal("35.00"),
        )

        rooms = [
            ("101", "Avery Brooks", "avery@example.com", Decimal("1250.00"), Decimal("75.00"), Decimal("900.00"), Decimal("900.00"), Decimal("0.00"), Decimal("0.00")),
            ("102", "Bianca Carter", "bianca@example.com", Decimal("1325.00"), Decimal("75.00"), Decimal("900.00"), Decimal("450.00"), Decimal("1325.00"), Decimal("75.00")),
            ("201", "Carlos Diaz", "carlos@example.com", Decimal("1195.00"), Decimal("70.00"), Decimal("800.00"), Decimal("800.00"), Decimal("0.00"), Decimal("0.00")),
            ("202", "Dana Ellis", "dana@example.com", Decimal("1425.00"), Decimal("85.00"), Decimal("950.00"), Decimal("950.00"), Decimal("425.00"), Decimal("0.00")),
        ]

        for index, (room, name, email, rent, utilities, deposit_required, deposit_paid, rent_balance, utility_balance) in enumerate(rooms, start=1):
            first_name, last_name = name.split(" ", 1)
            PropertyRoomRent.objects.create(
                property=property_obj,
                room_unit_label=room,
                monthly_rent=rent,
                utility_monthly=utilities,
                deposit_required=deposit_required,
                deposit_paid=deposit_paid,
            )
            CurrentResidentRosterEntry.objects.create(
                property=property_obj,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=f"541-555-20{index:02d}",
                room_unit_label=room,
                uploaded_by=admin,
            )

        demo_residents = []
        for index, (room, name, email, rent, utilities, deposit_required, deposit_paid, rent_balance, utility_balance) in enumerate(rooms, start=1):
            tenant_user = User.objects.create_user(
                username=f"demo-tenant-{room}",
                email=email,
                password="DemoPass123!",
                role="tenant",
            )
            application = HousingApplication.objects.create(
                property=property_obj,
                user=tenant_user,
                full_name=name,
                phone=f"541-555-10{index:02d}",
                email=email,
                age=30 + index,
                space_type="Apartment",
                space_label=room,
                monthly_rent=rent,
                balance=rent_balance,
                rent_due_day=1,
                lease_start_date=date(2025, index, 1),
                deposit_required=deposit_required,
                deposit_paid=deposit_paid,
                utility_monthly=utilities,
                utility_balance=utility_balance,
                income_source="Employment",
                monthly_income=rent * Decimal("3.4"),
                housing_need="Demo resident profile.",
                sobriety_acknowledgment=True,
                unconditional_regard_acknowledgment=True,
            )
            demo_residents.append(application)

        now = timezone.now()
        for month in [1, 2, 3, 4, 5]:
            service_month = date(2026, month, 1)
            for application in demo_residents:
                Payment.objects.create(
                    application=application,
                    payment_type="rent",
                    payment_method="ach",
                    description=f"Demo {service_month.strftime('%B')} rent",
                    amount=application.monthly_rent,
                    status="completed",
                    received_at=timezone.make_aware(datetime(2026, month, min(application.rent_due_day, 28), 9, 0)),
                    service_month=service_month,
                    recorded_by=admin,
                )
                Payment.objects.create(
                    application=application,
                    payment_type="utility",
                    payment_method="ach",
                    description=f"Demo {service_month.strftime('%B')} utilities",
                    amount=application.utility_monthly,
                    status="completed",
                    received_at=timezone.make_aware(datetime(2026, month, min(application.rent_due_day, 28), 9, 10)),
                    service_month=service_month,
                    recorded_by=admin,
                )

        upload = FinancialUpload.objects.create(
            property=property_obj,
            name="Demo T12 Summary",
            file=ContentFile(b"demo,summary\n", name="demo_t12_summary.csv"),
            parsed_at=now,
            notes="Seeded demo summary data. This database resets automatically.",
        )
        for month, income, expenses, debt in [
            (1, "10500.00", "4350.00", "2800.00"),
            (2, "10675.00", "4625.00", "2800.00"),
            (3, "10820.00", "4405.00", "2800.00"),
            (4, "10910.00", "4920.00", "2800.00"),
            (5, "11100.00", "4515.00", "2800.00"),
        ]:
            FinancialEntry.objects.create(upload=upload, property_name=property_obj.name, sheet_name="Demo Summary", row_number=month, year=2026, month=month, entry_type="income", category="Rent and Other Income", amount=Decimal(income))
            FinancialEntry.objects.create(upload=upload, property_name=property_obj.name, sheet_name="Demo Summary", row_number=month + 20, year=2026, month=month, entry_type="operating_expense", category="Operating Expenses", amount=Decimal(expenses))
            FinancialEntry.objects.create(upload=upload, property_name=property_obj.name, sheet_name="Demo Summary", row_number=month + 40, year=2026, month=month, entry_type="debt_service", category="Debt Service", amount=Decimal(debt))

        for name in ["Repairs", "Utilities", "Insurance", "Capital Improvements"]:
            ExpenseCategory.objects.create(name=name, entry_type="capital_expense" if name == "Capital Improvements" else "operating_expense", created_by=admin)

        ResidentMessage.objects.create(
            application=demo_residents[1],
            message_type="maintenance",
            subject="Kitchen sink leak",
            message="Demo maintenance message: small leak under the kitchen sink.",
            status="submitted",
        )
        BlogPost.objects.create(
            property=property_obj,
            author=landlord,
            title="Demo Community Update",
            body="This is a private demo property blog post for residents, landlords, and owners.",
        )
        PropertyOwnerIntake.objects.create(
            full_name="Morgan Multifamily",
            company_name="Morgan Multifamily Group",
            email="owner-lead@example.com",
            phone="541-555-0199",
            property_count=3,
            total_units=86,
            property_types="multifamily",
            current_software="Spreadsheet and legacy accounting export",
            current_pain_points="Needs easier rent roll, T-12, owner reporting, receipt tracking, and resident communication.",
            desired_reports="T-12, Rent Roll, NOI, Utility Trends, Vendor Expense, Valuation Estimate",
            status="submitted",
        )
