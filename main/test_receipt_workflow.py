from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AccountingReceipt, AccountingReceiptSplit, ExpenseCategory, Property, User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
)
class ReceiptMonthlyWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="monthly-bills", email="monthly-bills@example.com",
            password="StrongPass123!", role="landlord", is_staff=True,
        )
        self.property = Property.objects.create(
            name="Monthly Bills Property", landlord_email=self.user.email,
        )
        self.internet = ExpenseCategory.objects.create(name="Internet", entry_type="operating_expense")
        self.phone = ExpenseCategory.objects.create(name="Phone", entry_type="operating_expense")
        self.client.login(username="monthly-bills", password="StrongPass123!")

    @patch("main.views.timezone.localdate", return_value=date(2026, 9, 8))
    def test_current_month_is_separate_from_archived_months(self, _mock_localdate):
        current = AccountingReceipt.objects.create(
            property=self.property, receipt_file="accounting_receipts/current.pdf",
            vendor="Current Vendor", receipt_date=date(2026, 9, 2), amount=Decimal("50.00"),
        )
        archived = AccountingReceipt.objects.create(
            property=self.property, receipt_file="accounting_receipts/archived.pdf",
            vendor="Archived Vendor", receipt_date=date(2026, 8, 2), amount=Decimal("75.00"),
        )

        response = self.client.get(reverse("accounting_receipts"))

        self.assertEqual(response.context["current_month"]["receipts"], [current])
        august = next(month for month in response.context["archived_months"] if month["number"] == 8)
        self.assertEqual(august["receipts"], [archived])
        self.assertContains(response, "This month starts with a clean page.", count=0)

    @patch("main.views.timezone.localdate", return_value=date(2026, 9, 8))
    def test_same_vendor_and_total_reuses_prior_split(self, _mock_localdate):
        prior = AccountingReceipt.objects.create(
            property=self.property, receipt_file="accounting_receipts/charter-august.pdf",
            vendor="Spectrum", receipt_date=date(2026, 8, 5), amount=Decimal("120.00"),
        )
        AccountingReceiptSplit.objects.create(
            receipt=prior, category=self.internet, entry_type="operating_expense",
            description="Internet", amount=Decimal("80.00"), created_by=self.user,
        )
        AccountingReceiptSplit.objects.create(
            receipt=prior, category=self.phone, entry_type="operating_expense",
            description="Phone", amount=Decimal("40.00"), created_by=self.user,
        )

        response = self.client.post(reverse("accounting_receipts"), {
            "property": self.property.id,
            "receipt_file": SimpleUploadedFile("charter-september.pdf", b"bill", content_type="application/pdf"),
            "vendor": "Charter",
            "receipt_date": "2026-09-05",
            "entry_type": "operating_expense",
            "description": "September Charter bill",
            "amount": "120.00",
            "payment_method": "other",
            "notes": "",
        })

        self.assertRedirects(response, reverse("accounting_receipts"))
        receipt = AccountingReceipt.objects.exclude(id=prior.id).get()
        splits = list(receipt.splits.order_by("amount").values_list("category__name", "amount"))
        self.assertEqual(splits, [("Phone", Decimal("40.00")), ("Internet", Decimal("80.00"))])

    def test_changed_total_does_not_reuse_prior_split(self):
        prior = AccountingReceipt.objects.create(
            property=self.property, receipt_file="accounting_receipts/charter-old.pdf",
            vendor="Charter", receipt_date=date(2026, 8, 5), amount=Decimal("120.00"),
        )
        AccountingReceiptSplit.objects.create(
            receipt=prior, category=self.internet, amount=Decimal("120.00"), created_by=self.user,
        )
        response = self.client.post(reverse("accounting_receipts"), {
            "property": self.property.id,
            "receipt_file": SimpleUploadedFile("charter-new.pdf", b"bill", content_type="application/pdf"),
            "vendor": "Charter", "receipt_date": "2026-09-05",
            "entry_type": "operating_expense", "amount": "125.00",
            "payment_method": "other", "description": "", "notes": "",
        })

        self.assertRedirects(response, reverse("accounting_receipts"))
        self.assertFalse(AccountingReceipt.objects.exclude(id=prior.id).get().splits.exists())
