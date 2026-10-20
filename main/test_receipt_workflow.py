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

    def test_property_workspace_never_lists_another_property_receipt(self):
        other_property = Property.objects.create(
            name="Other Managed Property", landlord_email=self.user.email,
        )
        AccountingReceipt.objects.create(
            property=self.property, receipt_file="accounting_receipts/ours.pdf",
            vendor="Our Vendor", receipt_date=date(2026, 9, 5), amount=Decimal("25.00"),
        )
        AccountingReceipt.objects.create(
            property=other_property, receipt_file="accounting_receipts/other.pdf",
            vendor="Other Vendor", receipt_date=date(2026, 9, 5), amount=Decimal("30.00"),
        )

        response = self.client.get(
            reverse("property_accounting_receipts", args=[self.property.id]),
            {"year": "2026"},
        )

        self.assertContains(response, "Our Vendor")
        self.assertNotContains(response, "Other Vendor")

    def test_landlord_cannot_open_another_landlords_receipt_workspace(self):
        other_property = Property.objects.create(
            name="Private Property", landlord_email="somebody-else@example.com",
        )

        response = self.client.get(reverse("property_accounting_receipts", args=[other_property.id]))

        self.assertEqual(response.status_code, 404)

    def test_owner_sees_all_owned_properties_but_not_another_owners_property(self):
        owner = User.objects.create_user(
            username="receipt-owner", email="owner@example.com",
            password="StrongPass123!", role="property_owner",
        )
        owned_one = Property.objects.create(name="Owner One", owner_email=owner.email)
        owned_two = Property.objects.create(name="Owner Two", owner_email=owner.email)
        not_owned = Property.objects.create(name="Not Owned", owner_email="other-owner@example.com")
        self.client.force_login(owner)

        picker = self.client.get(reverse("accounting_receipts"))
        self.assertContains(picker, owned_one.name)
        self.assertContains(picker, owned_two.name)
        self.assertNotContains(picker, not_owned.name)
        self.assertEqual(
            self.client.get(reverse("property_accounting_receipts", args=[not_owned.id])).status_code,
            404,
        )

    def test_new_receipt_file_is_stored_under_property_accounting_folders(self):
        response = self.client.post(reverse("property_accounting_receipts", args=[self.property.id]), {
            "property": self.property.id,
            "receipt_file": SimpleUploadedFile("power bill.pdf", b"bill", content_type="application/pdf"),
            "vendor": "Pacific Power",
            "receipt_date": "2026-09-05",
            "entry_type": "operating_expense",
            "category": self.internet.id,
            "amount": "90.00",
            "payment_method": "other",
            "description": "September power bill",
            "notes": "",
        })

        self.assertRedirects(response, reverse("property_accounting_receipts", args=[self.property.id]))
        receipt = AccountingReceipt.objects.get(vendor="Pacific Power")
        self.assertIn(
            f"accounting_receipts/property-{self.property.id}-monthly-bills-property/2026/09/"
            "pacific-power/operating_expense/internet/",
            receipt.receipt_file.name,
        )

    def test_approval_keeps_long_property_scoped_receipt_path(self):
        receipt_path = (
            f"accounting_receipts/property-{self.property.id}-monthly-bills-property/"
            "2026/09/pacific-power/operating_expense/internet/"
            "0123456789abcdef0123456789abcdef.pdf"
        )
        self.assertGreater(len(receipt_path), 100)
        receipt = AccountingReceipt.objects.create(
            property=self.property, receipt_file=receipt_path,
            vendor="Pacific Power", receipt_date=date(2026, 9, 5),
            category=self.internet, amount=Decimal("90.00"),
        )

        response = self.client.post(reverse("approve_accounting_receipt", args=[receipt.id]))

        self.assertRedirects(response, reverse("accounting_receipts"))
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, "approved")
        self.assertEqual(receipt.financial_upload.file.name, receipt_path)
        # SQLite does not enforce the varchar limit that PostgreSQL applies on save.
        self.assertLessEqual(
            len(receipt.financial_upload.file.name),
            receipt.financial_upload._meta.get_field("file").max_length,
        )
        self.assertEqual(receipt.financial_entry.upload_id, receipt.financial_upload_id)
        self.assertEqual(receipt.financial_entry.amount, Decimal("90.00"))
