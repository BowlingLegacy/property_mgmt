from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import (
    HousingApplication,
    Payment,
    Property,
    ResidentBalanceEntry,
    ResidentLateFeePolicy,
    SignedDocument,
    User,
)
from .late_fees import assess_late_fees, fee_due
from .lease_terms import LEASE_VERSION, INITIALS
from .views import resident_portal_rent_due, split_combined_payment

PT = ZoneInfo("America/Los_Angeles")


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class LateFeeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="fee-resident", password="StrongPass123!", role="tenant"
        )
        self.property = Property.objects.create(name="The Painted Lady Inn")
        self.app = HousingApplication.objects.create(
            user=self.user,
            property=self.property,
            full_name="Test Resident",
            phone="5550000000",
            age=40,
            income_source="Work",
            monthly_income=2000,
            housing_need="Housing",
            monthly_rent=650,
            utility_monthly=55,
            deposit_required=450,
            deposit_paid=450,
            lease_start_date=date(2026, 9, 1),
        )
        self.app.refresh_from_db()
        self.policy = ResidentLateFeePolicy.objects.create(
            application=self.app,
            enabled=True,
            fee_type="flat",
            amount=25,
            grace_days=4,
            effective_from=date(2026, 10, 1),
            confirmed_at=datetime(2026, 10, 1, tzinfo=PT),
        )

    def payment(self, amount=650, when=None, **kwargs):
        return Payment.objects.create(
            application=self.app,
            payment_type=kwargs.pop("payment_type", "rent"),
            amount=amount,
            status=kwargs.pop("status", "completed"),
            service_month=date(2026, 10, 1),
            received_at=when or datetime(2026, 10, 5, 23, 59, tzinfo=PT),
            **kwargs
        )

    def test_no_fee_on_pay_by_day_then_one_fee_on_next_day(self):
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 5))["assessed"], 0)
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 1)
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 0)
        self.assertEqual(fee_due(self.app), Decimal("25.00"))
        self.app.refresh_from_db()
        self.assertEqual(self.app.balance, 0)

    def test_paid_rent_with_unpaid_utilities_deposit_or_fees_does_not_trigger(self):
        self.payment()
        self.app.utility_balance = 100
        self.app.deposit_paid = 0
        self.app.save()
        ResidentBalanceEntry.objects.create(
            application=self.app,
            entry_kind="charge",
            balance_type="late_fee",
            amount=25,
            service_month=date(2026, 9, 1),
        )
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 0)

    def test_pending_payment_does_not_satisfy_rent(self):
        self.payment(status="pending")
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 1)

    def test_partial_rent_remains_delinquent(self):
        self.payment(amount=649)
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 1)

    def test_late_payment_still_gets_fee_when_job_recovers(self):
        self.payment(when=datetime(2026, 10, 6, 0, 1, tzinfo=PT))
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 7))["assessed"], 1)

    def test_utc_timestamp_on_fifth_pacific_is_on_time(self):
        self.payment(when=datetime(2026, 10, 6, 6, 59, tzinfo=ZoneInfo("UTC")))
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 0)

    def test_dry_run_makes_no_entries(self):
        self.assertEqual(
            assess_late_fees(as_of=date(2026, 10, 6), dry_run=True)["would_assess"], 1
        )
        self.assertFalse(ResidentBalanceEntry.objects.exists())

    def test_new_move_in_future_and_former_residents_are_skipped(self):
        for changes in [
            dict(lease_start_date=date(2026, 10, 18)),
            dict(tenancy_status="former"),
            dict(move_out_date=date(2026, 10, 5)),
        ]:
            with self.subTest(changes=changes):
                for k, v in changes.items():
                    setattr(self.app, k, v)
                self.app.save()
                self.assertEqual(
                    assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 0
                )

    def test_no_retroactive_fee_before_policy_effective_date(self):
        self.policy.effective_from = date(2026, 10, 19)
        self.policy.save()
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 19))["assessed"], 0)

    def test_percent_policy_uses_ninth_after_eighth_deadline(self):
        self.policy.fee_type = "percent"
        self.policy.amount = 5
        self.policy.grace_days = 7
        self.policy.save()
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 8))["assessed"], 0)
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 9))["assessed"], 1)
        self.assertEqual(fee_due(self.app), Decimal("32.50"))

    def test_manual_monthly_fee_or_waiver_is_not_rebilled(self):
        ResidentBalanceEntry.objects.create(
            application=self.app,
            entry_kind="charge",
            balance_type="late_fee",
            amount=25,
            service_month=date(2026, 10, 1),
        )
        ResidentBalanceEntry.objects.create(
            application=self.app,
            entry_kind="credit",
            balance_type="late_fee",
            amount=25,
            service_month=date(2026, 10, 1),
        )
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 0)
        self.assertEqual(fee_due(self.app), 0)

    def test_linked_resident_files_cannot_receive_duplicate_monthly_fees(self):
        self.app.space_label = "A"
        self.app.save()
        duplicate = HousingApplication.objects.create(
            property=self.property,
            full_name=self.app.full_name,
            phone=self.app.phone,
            age=40,
            income_source="Work",
            monthly_income=2000,
            housing_need="Duplicate historical file",
            space_label="A",
            monthly_rent=650,
            lease_start_date=date(2026, 9, 1),
        )
        ResidentLateFeePolicy.objects.create(
            application=duplicate,
            enabled=True,
            amount=25,
            grace_days=4,
            effective_from=date(2026, 10, 1),
            confirmed_at=datetime(2026, 10, 1, tzinfo=PT),
        )
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 1)
        self.assertEqual(fee_due(self.app), 25)

    def test_current_month_service_credit_can_clear_rent(self):
        self.payment(payment_method="service_credit")
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 0)

    def test_profile_due_day_change_does_not_change_agreed_deadline(self):
        self.app.rent_due_day = 15
        self.app.save()
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 1)

    def test_no_policy_confirmation_means_no_automatic_charge(self):
        self.policy.confirmed_at = None
        self.policy.save()
        self.assertEqual(assess_late_fees(as_of=date(2026, 10, 6))["assessed"], 0)

    def test_fee_is_separate_from_rent_and_combined_payment_pays_it(self):
        assess_late_fees(as_of=date(2026, 10, 6))
        with patch(
            "main.views.current_month_bounds",
            return_value=(date(2026, 10, 1), date(2026, 11, 1)),
        ):
            self.assertEqual(resident_portal_rent_due(self.app), 650)
            combined = self.payment(
                amount=730,
                payment_type="other",
                description="Combined Payment - Total Due",
            )
            self.assertTrue(split_combined_payment(combined))
        self.assertEqual(Payment.objects.filter(payment_type="rent").get().amount, 650)
        self.assertEqual(
            Payment.objects.filter(payment_type="utility").get().amount, 55
        )
        self.assertEqual(
            Payment.objects.filter(payment_type="late_fee").get().amount, 25
        )
        self.assertEqual(fee_due(self.app), 0)

    @override_settings(LATE_FEE_JOB_TOKEN="test-secret")
    def test_scheduled_endpoint_requires_token_and_post_and_supports_dry_run(self):
        url = reverse("assess_late_fees_job")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(
            self.client.post(url, {}, content_type="application/json").status_code, 403
        )
        with patch(
            "main.cron_views.assess_late_fees",
            return_value={"would_assess": 1, "assessed": 0},
        ) as run:
            r = self.client.post(
                url,
                {"dry_run": True},
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer test-secret",
            )
        self.assertEqual(r.status_code, 200)
        run.assert_called_once_with(dry_run=True)
        self.assertEqual(
            self.client.post(
                url,
                {"as_of": "2020-01-01"},
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer test-secret",
            ).status_code,
            400,
        )


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class LeaseVersionTests(TestCase):
    def setUp(self):
        LateFeeTests.setUp(self)
        self.lease = SignedDocument.objects.create(
            application=self.app,
            document_type="lease",
            title="Resident Lease Agreement",
        )
        self.client.force_login(self.user)

    def test_new_lease_keeps_painted_lady_terms_and_adds_notice_provisions(self):
        r = self.client.get(reverse("onboarding_document", args=[self.lease.pk]))
        for text in [
            "30-Day Written Move-Out Notice",
            "$25.00",
            "sixth (6th)",
            "First-90-day",
            "recovery programs is encouraged",
            "Shared Utilities",
            "31 days",
            "physical mailing address",
        ]:
            self.assertContains(r, text)
        self.assertEqual(self.lease.lease_version, LEASE_VERSION)

    def test_signed_lease_keeps_accepted_text_and_financial_particulars(self):
        data = {name: "TR" for name, _ in INITIALS}
        data.update(resident_signature="Test Resident", signature_agreement="on")
        r = self.client.post(
            reverse("submit_onboarding_document", args=[self.lease.pk]), data
        )
        self.assertEqual(r.status_code, 302)
        self.lease.refresh_from_db()
        saved = self.lease.signed_lease_html
        self.assertTrue(self.lease.locked)
        self.assertIn("$650.00", saved)
        self.app.monthly_rent = 900
        self.app.save()
        self.lease.save()
        self.lease.refresh_from_db()
        self.assertEqual(self.lease.monthly_rent, 650)
        self.assertEqual(self.lease.signed_lease_html, saved)
        self.assertTrue(ResidentLateFeePolicy.objects.get(application=self.app).enabled)

    def test_legacy_signed_lease_uses_preserved_template(self):
        self.lease.lease_version = "legacy"
        self.lease.locked = True
        self.lease.save()
        r = self.client.get(reverse("onboarding_document", args=[self.lease.pk]))
        self.assertTemplateUsed(r, "lease_sign_legacy.html")
        self.assertContains(r, "June 2026 platform transition")
        self.assertNotContains(r, "30-Day Written Move-Out Notice")

    def test_missing_initials_cannot_sign_new_agreement(self):
        self.client.post(
            reverse("submit_onboarding_document", args=[self.lease.pk]),
            {"resident_signature": "Test Resident", "signature_agreement": "on"},
        )
        self.lease.refresh_from_db()
        self.assertFalse(self.lease.locked)


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class LateFeePortalTests(TestCase):
    def setUp(self):
        LateFeeTests.setUp(self)
        self.staff = User.objects.create_superuser(
            username="fee-admin",
            email="feeadmin@example.com",
            password="StrongPass123!",
            role="admin",
        )

    def test_policy_enable_requires_confirmation_and_cannot_be_backdated(self):
        self.policy.enabled = False
        self.policy.save()
        self.client.force_login(self.staff)
        data = {
            "action": "late_fee_policy",
            "enabled": "on",
            "fee_type": "flat",
            "amount": "25.00",
            "rent_due_day": 1,
            "grace_days": 4,
            "effective_from": "2026-11-01",
        }
        r = self.client.post(
            reverse("edit_resident_balances", args=[self.app.pk]), data
        )
        self.assertContains(r, "Confirm the signed terms")
        self.policy.refresh_from_db()
        self.assertFalse(self.policy.enabled)
        data["confirm_agreed_terms"] = "on"
        with patch("django.utils.timezone.localdate", return_value=date(2026, 10, 19)):
            r = self.client.post(
                reverse("edit_resident_balances", args=[self.app.pk]), data
            )
        self.assertEqual(r.status_code, 302)
        self.policy.refresh_from_db()
        self.assertTrue(self.policy.enabled)
        data["effective_from"] = "2026-10-01"
        data["amount"] = "50"
        with patch("django.utils.timezone.localdate", return_value=date(2026, 10, 19)):
            r = self.client.post(
                reverse("edit_resident_balances", args=[self.app.pk]), data
            )
        self.assertContains(r, "cannot be backdated")
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.amount, 25)

    def test_manual_late_fee_uses_fee_ledger_not_rent(self):
        self.client.force_login(self.staff)
        r = self.client.post(
            reverse("edit_resident_balances", args=[self.app.pk]),
            {
                "action": "adjust",
                "service_month": "2026-10",
                "late_fee_charge": "25.00",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.app.refresh_from_db()
        self.assertEqual(self.app.balance, 0)
        self.assertEqual(fee_due(self.app), 25)

    def test_portal_shows_and_pays_fees_separately(self):
        assess_late_fees(as_of=date(2026, 10, 6))
        self.client.force_login(self.user)
        with patch(
            "main.views.current_month_bounds",
            return_value=(date(2026, 10, 1), date(2026, 11, 1)),
        ):
            r = self.client.get(reverse("resident_balance_detail"))
            self.assertEqual(r.context["rent_due"], 650)
            self.assertEqual(r.context["late_fee_due"], 25)
            self.assertEqual(r.context["total_due"], 730)
            self.assertContains(r, "Pay Late Fees")
            with override_settings(DEMO_MODE=True):
                r = self.client.get(
                    reverse("pay_by_type", args=[self.app.pk, "late_fee"])
                )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Payment.objects.get(payment_type="late_fee").amount, 25)
        self.assertEqual(fee_due(self.app), 0)
