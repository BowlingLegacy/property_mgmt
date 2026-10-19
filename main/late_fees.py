"""Assess agreed late fees once, without turning them into rent."""

import calendar
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import (
    HousingApplication,
    Payment,
    ResidentBalanceEntry,
    ResidentLateFeePolicy,
)

PACIFIC = ZoneInfo("America/Los_Angeles")
ZERO = Decimal("0.00")


def fee_due(application):
    if not application:
        return ZERO
    from .views import resident_related_application_ids

    ids = resident_related_application_ids(application)
    rows = ResidentBalanceEntry.objects.filter(
        application_id__in=ids, balance_type="late_fee"
    )
    charges = (
        rows.filter(entry_kind="charge").aggregate(total=Sum("amount"))["total"] or ZERO
    )
    credits = (
        rows.filter(entry_kind="credit").aggregate(total=Sum("amount"))["total"] or ZERO
    )
    paid = (
        Payment.objects.filter(
            application_id__in=ids, payment_type="late_fee", status="completed"
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    return max(charges - credits - paid, ZERO)


def deadline_for(policy, month):
    due_day = min(
        max(policy.rent_due_day, 1), calendar.monthrange(month.year, month.month)[1]
    )
    due_date = month.replace(day=due_day)
    # At least the statutory four-day rental-period protection; later lease deadlines control.
    fee_date = due_date + timedelta(days=max(policy.grace_days, 3) + 1)
    return fee_date, datetime.combine(fee_date, time.min, tzinfo=PACIFIC)


def unpaid_rent_at_deadline(policy, month, cutoff):
    from .views import (
        expected_rent_for_month,
        payment_amount_for_month,
        resident_related_application_ids,
    )

    app = policy.application
    related = resident_related_application_ids(app)
    payments = []
    for p in Payment.objects.filter(
        application_id__in=related, payment_type="rent", status="completed"
    ):
        received = p.received_at or p.created_at
        if received < cutoff:
            payments.append(p)
    paid = payment_amount_for_month(payments, month.year, month.month, ["rent"])
    entries = ResidentBalanceEntry.objects.filter(
        application_id__in=related,
        balance_type="rent",
        service_month=month,
        created_at__lt=cutoff,
    )
    charges = (
        entries.filter(entry_kind="charge").aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    credits = (
        entries.filter(entry_kind="credit").aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    expected = expected_rent_for_month(app, month)
    return max(expected + charges - credits - paid, ZERO)


def assess_late_fees(*, as_of=None, dry_run=False):
    today = as_of or timezone.localtime(timezone.now(), PACIFIC).date()
    month = today.replace(day=1)
    previous = (month - timedelta(days=1)).replace(day=1)
    result = {"assessed": 0, "would_assess": 0, "skipped": 0, "date": today.isoformat()}
    policies = ResidentLateFeePolicy.objects.filter(enabled=True).select_related(
        "application", "application__property", "agreed_lease"
    )
    for candidate in policies:
        for service_month in (previous, month):
            with transaction.atomic():
                policy = (
                    ResidentLateFeePolicy.objects.select_for_update(of=("self",))
                    .select_related("application", "agreed_lease")
                    .get(pk=candidate.pk)
                )
                app = policy.application
                fee_date, cutoff = deadline_for(policy, service_month)
                if (
                    not policy.enabled
                    or not policy.confirmed_at
                    or policy.effective_from > fee_date
                    or today < fee_date
                    or app.tenancy_status != "active"
                    or (app.lease_start_date and app.lease_start_date >= fee_date)
                    or (app.move_out_date and app.move_out_date < fee_date)
                ):
                    result["skipped"] += 1
                    continue
                if policy.agreed_lease_id and (
                    not policy.agreed_lease.locked
                    or not policy.agreed_lease.signed_at
                    or policy.agreed_lease.signed_at >= cutoff
                ):
                    result["skipped"] += 1
                    continue
                from .views import resident_related_application_ids

                related_ids = resident_related_application_ids(app)
                # Keep waivers and manually posted fees across linked resident files.
                if (
                    ResidentBalanceEntry.objects.filter(
                        application_id__in=related_ids,
                        balance_type="late_fee",
                        entry_kind="charge",
                        service_month=service_month,
                    ).exists()
                    or ResidentBalanceEntry.objects.filter(
                        application_id__in=related_ids,
                        description="Late fee charge",
                        entry_kind="charge",
                        service_month=service_month,
                    ).exists()
                ):
                    result["skipped"] += 1
                    continue
                unpaid = unpaid_rent_at_deadline(policy, service_month, cutoff)
                if unpaid <= 0:
                    result["skipped"] += 1
                    continue
                from .views import historical_rent_for_month

                base = historical_rent_for_month(app, service_month)
                amount = (
                    policy.amount
                    if policy.fee_type == "flat"
                    else base * policy.amount / Decimal("100")
                )
                amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if amount <= 0:
                    result["skipped"] += 1
                    continue
                if dry_run:
                    result["would_assess"] += 1
                    continue
                _, created = ResidentBalanceEntry.objects.get_or_create(
                    assessment_key=f"late:{min(related_ids)}:{service_month:%Y-%m}",
                    defaults=dict(
                        application=app,
                        entry_kind="charge",
                        balance_type="late_fee",
                        amount=amount,
                        service_month=service_month,
                        description="Automatic late fee",
                        notes=f"Rent unpaid at {fee_date.isoformat()} 00:00 America/Los_Angeles: ${unpaid}. Agreed policy {policy.pk}.",
                    ),
                )
                result["assessed" if created else "skipped"] += 1
    return result
