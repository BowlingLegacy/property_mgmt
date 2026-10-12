from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    FinancialEntry,
    FinancialUpload,
    HousingApplication,
    LandlordIntake,
    Payment,
    Property,
    ResidentBalanceEntry,
)
from .views import payment_month_allocations, rent_roll_rows_for_properties, t12_report_rows


User = get_user_model()


def resident(property_obj, name, **overrides):
    values = {
        "property": property_obj,
        "full_name": name,
        "phone": "555-0100",
        "email": f"{name.lower().replace(' ', '.')}@example.com",
        "age": 40,
        "income_source": "Synthetic",
        "monthly_income": Decimal("2000.00"),
        "housing_need": "Synthetic fixture",
        "application_folder": "active",
        "tenancy_status": "active",
        "space_label": "A",
        "monthly_rent": Decimal("650.00"),
        "utility_monthly": Decimal("0.00"),
        "lease_start_date": date(2026, 1, 1),
        "landlord_reviewed_at": date(2026, 1, 1),
    }
    values.update(overrides)
    return HousingApplication.objects.create(**values)


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class ComprehensiveReportRegressionTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            username="report-auditor", email="audit@example.com", password="StrongPass123!",
            role="landlord", is_staff=True,
        )
        LandlordIntake.objects.create(user=self.landlord, email=self.landlord.email, status="registered")
        self.a = Property.objects.create(name="Audit A", landlord_email=self.landlord.email)
        self.b = Property.objects.create(name="Audit B", landlord_email=self.landlord.email)
        self.client.force_login(self.landlord)

    def upload(self, property_obj, name="summary", ledger_scope="property"):
        return FinancialUpload.objects.create(
            property=property_obj, ledger_scope=ledger_scope, name=name,
            file=SimpleUploadedFile(f"{name}.csv", b"date,amount\n"),
        )

    def entry(self, upload, property_obj, amount, entry_type="income", month=1, **overrides):
        values = {
            "upload": upload,
            "property": property_obj,
            "ledger_scope": "property" if property_obj else upload.ledger_scope,
            "property_name": property_obj.name if property_obj else "Company",
            "sheet_name": "Summary",
            "row_number": FinancialEntry.objects.count() + 1,
            "year": 2026,
            "month": month,
            "entry_type": entry_type,
            "category": "Rent" if entry_type == "income" else "Synthetic expense",
            "amount": amount,
        }
        values.update(overrides)
        return FinancialEntry.objects.create(**values)

    def test_allocation_rounding_and_income_statement_use_service_months(self):
        app = resident(self.a, "Allocation Resident")
        payment = Payment.objects.create(
            application=app, payment_type="rent", payment_method="cash", status="completed",
            amount=Decimal("100.00"), service_month=date(2026, 1, 1), months_covered=3,
        )
        self.assertEqual(list(payment_month_allocations(payment)), [
            (date(2026, 1, 1), Decimal("33.33")),
            (date(2026, 2, 1), Decimal("33.33")),
            (date(2026, 3, 1), Decimal("33.34")),
        ])
        response = self.client.get(reverse("custom_reports"), {
            "report_type": "income_statement", "property_id": self.a.id,
            "start_date": "2026-01-01", "end_date": "2026-03-31",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totals"]["Total Income"], Decimal("100.00"))

    def test_portfolio_precedence_is_per_property(self):
        self.entry(self.upload(self.a, "a-summary"), self.a, Decimal("1000.00"))
        app = resident(self.b, "Portal Resident", space_label="B")
        Payment.objects.create(
            application=app, payment_type="rent", payment_method="cash", status="completed",
            amount=Decimal("700.00"), service_month=date(2026, 1, 1),
        )
        months, totals = t12_report_rows(self.landlord, 2026, Property.objects.filter(id__in=[self.a.id, self.b.id]))
        self.assertEqual(months[0]["spreadsheet_income"], Decimal("1000.00"))
        self.assertEqual(months[0]["online_income"], Decimal("700.00"))
        self.assertEqual(totals["total_income"], Decimal("1700.00"))

    def test_row_level_attribution_excludes_bank_and_company_rows(self):
        upload = self.upload(self.a, "mixed-bank", "bank")
        self.entry(upload, self.a, Decimal("100.00"), entry_type="operating_expense")
        self.entry(upload, self.b, Decimal("200.00"), entry_type="operating_expense")
        self.entry(upload, None, Decimal("300.00"), entry_type="operating_expense", ledger_scope="company")
        a_months, _ = t12_report_rows(self.landlord, 2026, Property.objects.filter(id=self.a.id))
        b_months, _ = t12_report_rows(self.landlord, 2026, Property.objects.filter(id=self.b.id))
        self.assertEqual(a_months[0]["operating_expenses"], Decimal("100.00"))
        self.assertEqual(b_months[0]["operating_expenses"], Decimal("200.00"))

    def test_deposit_liability_is_remaining_held_and_includes_former(self):
        app = resident(
            self.a, "Former Deposit", tenancy_status="former", application_folder="archived",
            move_out_date=date(2026, 6, 1), deposit_required=Decimal("450.00"),
            deposit_paid=Decimal("450.00"),
        )
        ResidentBalanceEntry.objects.create(
            application=app, entry_kind="credit", balance_type="rent", amount=Decimal("150.00"),
            description="Security deposit applied to balance",
        )
        response = self.client.get(reverse("custom_reports"), {
            "report_type": "deposit_liability", "property_id": self.a.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totals"]["Deposit Held"], Decimal("300.00"))
        self.assertContains(response, "Former Deposit")

    def test_move_out_allocates_same_service_month_payment_then_only_needed_deposit(self):
        app = resident(self.a, "Move Out", balance=Decimal("300.00"), deposit_paid=Decimal("800.00"), deposit_required=Decimal("800.00"))
        ResidentBalanceEntry.objects.create(
            application=app, entry_kind="charge", balance_type="rent", amount=Decimal("500.00"),
            service_month=date(2026, 6, 1), description="Move-out charge",
        )
        Payment.objects.create(
            application=app, payment_type="rent", payment_method="cash", status="completed",
            amount=Decimal("200.00"), service_month=date(2026, 6, 1),
        )
        response = self.client.get(reverse("move_out_statement", args=[app.id]))
        self.assertEqual(response.context["allocated_payment_total"], Decimal("200.00"))
        self.assertEqual(response.context["move_out_balance_before_deposit"], Decimal("300.00"))
        self.assertEqual(response.context["statement_deposit_credit"], Decimal("300.00"))
        self.assertEqual(response.context["deposit_remaining_after_statement"], Decimal("500.00"))
        self.assertEqual(response.context["final_balance"], Decimal("0.00"))

    @patch("main.views.timezone.localdate", return_value=date(2026, 10, 12))
    def test_future_tenant_does_not_overwrite_current_room(self, _today):
        current = resident(self.a, "Current A", lease_start_date=date(2026, 1, 1))
        resident(self.a, "Future Z", lease_start_date=date(2026, 11, 1))
        Payment.objects.create(
            application=current, payment_type="rent", payment_method="cash", status="completed",
            amount=Decimal("100.00"), service_month=date(2026, 10, 1),
        )
        rows = rent_roll_rows_for_properties(self.landlord, date(2026, 10, 1), Property.objects.filter(id=self.a.id))
        self.assertEqual([row["resident"] for row in rows], ["Current A"])
        self.assertEqual(rows[0]["rent_paid"], Decimal("100.00"))

    def test_reversed_date_range_shows_error_and_no_report(self):
        response = self.client.get(reverse("custom_reports"), {
            "report_type": "payment_summary", "start_date": "2026-03-02", "end_date": "2026-02-28",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["generated"])
        self.assertContains(response, "Start date must be on or before end date")

    @patch("main.views.timezone.localdate", return_value=date(2026, 1, 31))
    def test_projection_does_not_annualize_future_allocations_twice(self, _today):
        app = resident(self.a, "Annual Allocation")
        Payment.objects.create(
            application=app, payment_type="rent", payment_method="cash", status="completed",
            amount=Decimal("1200.00"), service_month=date(2026, 1, 1), months_covered=12,
        )
        _months, totals = t12_report_rows(self.landlord, 2026, Property.objects.filter(id=self.a.id))
        self.assertEqual(totals["net_cash_flow"], Decimal("1200.00"))
        self.assertEqual(totals["projected_annual_cash_flow"], Decimal("1200.00"))
