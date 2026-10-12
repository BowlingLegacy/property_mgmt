from decimal import Decimal
import threading
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from .models import ApplicantDocument, HousingApplication, LandlordIntake, Payment, Property, PropertyOwnerIntake


User = get_user_model()


def create_application(**overrides):
    values = {
        "full_name": "Synthetic Applicant",
        "phone": "555-0100",
        "email": "applicant@example.com",
        "age": 30,
        "income_source": "Synthetic wages",
        "monthly_income": Decimal("2000.00"),
        "housing_need": "Synthetic test housing need",
    }
    values.update(overrides)
    return HousingApplication.objects.create(**values)


def stripe_event(payment_id, session_id="cs_test", amount_total=2500):
    return {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": session_id,
            "metadata": {"payment_id": str(payment_id)},
            "payment_intent": "pi_test",
            "payment_method_types": ["card"],
            "payment_status": "paid",
            "currency": "usd",
            "amount_total": amount_total,
        }},
    }


class PrivateApplicationAccessTests(TestCase):
    def setUp(self):
        self.first = Property.objects.create(name="First", landlord_email="first@example.com")
        self.second = Property.objects.create(name="Second", landlord_email="second@example.com")
        self.application = create_application(property=self.first)
        self.other_landlord = User.objects.create_user(
            username="other", email="second@example.com", password="test-pass", role="landlord"
        )
        LandlordIntake.objects.create(
            user=self.other_landlord, email="second@example.com", status="registered"
        )

    def test_printable_application_requires_login(self):
        response = self.client.get(reverse("printable_application", args=[self.application.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_cross_property_printable_application_is_denied(self):
        self.client.force_login(self.other_landlord)
        response = self.client.get(reverse("printable_application", args=[self.application.id]))
        self.assertEqual(response.status_code, 404)

    def test_property_scope_uses_invite_identity_not_mutable_account_email(self):
        landlord = User.objects.create_user(
            username="first", email="changed@example.com", password="test-pass", role="landlord"
        )
        LandlordIntake.objects.create(
            user=landlord, email="first@example.com", status="registered"
        )
        self.client.force_login(landlord)
        allowed = self.client.get(reverse("printable_application", args=[self.application.id]))
        self.assertEqual(allowed.status_code, 200)

    @override_settings(MEDIA_ROOT="tmp/test-private-media")
    def test_private_document_is_streamed_only_through_scoped_view(self):
        document = ApplicantDocument.objects.create(
            application=self.application,
            name="Synthetic ID",
            document_type="id",
            file=SimpleUploadedFile("synthetic-id.txt", b"private"),
        )
        self.client.force_login(self.other_landlord)
        denied = self.client.get(reverse("open_applicant_document", args=[document.id]))
        self.assertEqual(denied.status_code, 404)
        public = self.client.get(document.file.url)
        self.assertEqual(public.status_code, 404)


class InviteIdentityTests(TestCase):
    def test_signup_rejects_email_different_from_invitation(self):
        pending = User.objects.create_user(
            username="pending-owner", email="invited@example.com", role="property_owner"
        )
        pending.set_unusable_password()
        pending.save()
        pending.refresh_invite_code()
        PropertyOwnerIntake.objects.create(
            user=pending,
            full_name="Invited Owner",
            email="invited@example.com",
            phone="555-0100",
            status="invited",
        )
        session = self.client.session
        session["pending_portal_user_id"] = pending.id
        session.save()

        response = self.client.post(reverse("signup"), {
            "username": "claimed-owner",
            "email": "attacker@example.com",
            "password1": "A-secure-test-password-781!",
            "password2": "A-secure-test-password-781!",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use the email address that received this invite")
        self.assertFalse(User.objects.filter(username="claimed-owner").exists())


class StripeWebhookTests(TestCase):
    def setUp(self):
        property_obj = Property.objects.create(name="Webhook Property")
        self.application = create_application(
            property=property_obj,
            full_name="Synthetic Resident",
            email="resident@example.com",
            balance=Decimal("100.00"),
        )
        self.payment = Payment.objects.create(
            application=self.application,
            payment_type="rent",
            amount=Decimal("25.00"),
            status="pending",
            stripe_session_id="cs_test",
        )

    @patch("main.views.send_mail")
    @patch("main.views.stripe.Webhook.construct_event")
    def test_repeated_webhook_applies_payment_once(self, construct_event, send_mail):
        construct_event.return_value = stripe_event(self.payment.id)
        url = reverse("stripe_webhook")
        self.assertEqual(self.client.post(url, b"{}", content_type="application/json").status_code, 200)
        self.assertEqual(self.client.post(url, b"{}", content_type="application/json").status_code, 200)
        self.application.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.application.balance, Decimal("75.00"))
        self.assertEqual(self.payment.status, "completed")
        self.assertEqual(send_mail.call_count, 1)

    @patch("main.views.stripe.Webhook.construct_event")
    def test_interrupted_balance_update_rolls_back_completion(self, construct_event):
        construct_event.return_value = stripe_event(self.payment.id)

        def interrupted(payment):
            payment.application.balance = Decimal("1.00")
            payment.application.save(update_fields=["balance"])
            raise RuntimeError("synthetic interruption")

        with patch("main.views.apply_completed_payment_to_balance", side_effect=interrupted):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("stripe_webhook"), b"{}", content_type="application/json")
        self.application.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.application.balance, Decimal("100.00"))
        self.assertEqual(self.payment.status, "pending")

    @patch("main.views.stripe.Webhook.construct_event")
    def test_mismatched_checkout_amount_is_rejected(self, construct_event):
        construct_event.return_value = stripe_event(self.payment.id, amount_total=2400)
        response = self.client.post(reverse("stripe_webhook"), b"{}", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.application.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.application.balance, Decimal("100.00"))
        self.assertEqual(self.payment.status, "pending")


class StripeConcurrencyContractTests(TransactionTestCase):
    reset_sequences = True

    @patch("main.views.send_mail")
    @patch("main.views.stripe.Webhook.construct_event")
    def test_concurrent_webhooks_apply_balance_once(self, construct_event, _send_mail):
        if not connection.features.has_select_for_update:
            self.skipTest("SQLite does not provide SELECT FOR UPDATE; production database must run this contract test.")

        # Historical data migrations insert explicit primary keys without advancing
        # PostgreSQL sequences, so use isolated high IDs for this locking contract.
        property_obj = Property.objects.create(id=990001, name="Concurrent Property")
        application = create_application(
            id=990001,
            property=property_obj,
            full_name="Concurrent Synthetic Resident",
            email="concurrent@example.com",
            balance=Decimal("100.00"),
        )
        payment = Payment.objects.create(
            id=990001,
            application=application,
            payment_type="rent",
            amount=Decimal("25.00"),
            status="pending",
            stripe_session_id="cs_concurrent",
        )
        construct_event.return_value = stripe_event(payment.id, session_id="cs_concurrent")
        barrier = threading.Barrier(2)
        statuses = []
        errors = []

        def deliver():
            try:
                from django.test import Client
                barrier.wait(timeout=5)
                statuses.append(Client().post(
                    reverse("stripe_webhook"), b"{}", content_type="application/json"
                ).status_code)
            except Exception as exc:
                errors.append(exc)
            finally:
                from django.db import connections
                connections.close_all()

        threads = [threading.Thread(target=deliver), threading.Thread(target=deliver)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(errors)
        self.assertEqual(sorted(statuses), [200, 200])
        application.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(application.balance, Decimal("75.00"))
        self.assertEqual(payment.status, "completed")

    @patch("main.views.send_mail")
    @patch("main.views.stripe.Webhook.construct_event")
    def test_concurrent_distinct_payments_both_apply_once(self, construct_event, _send_mail):
        if not connection.features.has_select_for_update:
            self.skipTest("SQLite does not provide SELECT FOR UPDATE; production database must run this contract test.")

        property_obj = Property.objects.create(id=990002, name="Concurrent Distinct Property")
        application = create_application(
            id=990002, property=property_obj, full_name="Distinct Synthetic Resident",
            email="distinct@example.com", balance=Decimal("100.00"),
        )
        first = Payment.objects.create(
            id=990002, application=application, payment_type="rent", amount=Decimal("25.00"),
            status="pending", stripe_session_id="cs_distinct_1",
        )
        second = Payment.objects.create(
            id=990003, application=application, payment_type="rent", amount=Decimal("25.00"),
            status="pending", stripe_session_id="cs_distinct_2",
        )

        def event_for_payload(payload, *_args):
            return stripe_event(
                first.id if payload == b"first" else second.id,
                session_id="cs_distinct_1" if payload == b"first" else "cs_distinct_2",
            )

        construct_event.side_effect = event_for_payload
        barrier = threading.Barrier(2)
        statuses = []
        errors = []

        def deliver(payload):
            try:
                from django.test import Client
                barrier.wait(timeout=5)
                statuses.append(Client().post(
                    reverse("stripe_webhook"), payload, content_type="application/json"
                ).status_code)
            except Exception as exc:
                errors.append(exc)
            finally:
                from django.db import connections
                connections.close_all()

        threads = [threading.Thread(target=deliver, args=(b"first",)), threading.Thread(target=deliver, args=(b"second",))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(errors)
        self.assertEqual(sorted(statuses), [200, 200])
        application.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(application.balance, Decimal("50.00"))
        self.assertEqual(first.status, "completed")
        self.assertEqual(second.status, "completed")
