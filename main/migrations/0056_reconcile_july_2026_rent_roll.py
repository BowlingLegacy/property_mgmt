from datetime import date
from decimal import Decimal

from django.db import migrations
from django.db.models import Q, Sum
from django.utils import timezone


JULY = date(2026, 7, 1)
AUGUST = date(2026, 8, 1)
MARKER = "July 2026 rent roll reconciliation migration 0056"


def month_payment_query(service_month):
    return (
        Q(service_month=service_month)
        | Q(
            service_month__isnull=True,
            received_at__year=service_month.year,
            received_at__month=service_month.month,
        )
        | Q(
            service_month__isnull=True,
            received_at__isnull=True,
            created_at__year=service_month.year,
            created_at__month=service_month.month,
        )
    )


def resident_for_name(HousingApplication, name):
    return (
        HousingApplication.objects
        .filter(full_name__iexact=name, property_id__isnull=False)
        .order_by("-id")
        .first()
    )


def room_amount(PropertyRoomRent, resident, room, field, fallback):
    setting = (
        PropertyRoomRent.objects
        .filter(property_id=resident.property_id)
        .filter(Q(room_unit_label__iexact=room) | Q(room_unit_label__iexact=f"Room {room}"))
        .order_by("-id")
        .first()
    )
    amount = getattr(setting, field, None) if setting else None
    if amount is None or amount <= 0:
        amount = getattr(resident, field, None) or fallback
    return Decimal(amount)


def ensure_payment(Payment, resident, payment_type, target, service_month=JULY):
    paid = (
        Payment.objects
        .filter(application_id=resident.id, payment_type=payment_type, status="completed")
        .filter(month_payment_query(service_month))
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    difference = max(Decimal(target) - paid, Decimal("0.00"))
    if difference:
        Payment.objects.create(
            application_id=resident.id,
            payment_type=payment_type,
            payment_method="other",
            amount=difference,
            status="completed",
            received_at=timezone.now(),
            service_month=service_month,
            months_covered=1,
            description=f"{service_month.strftime('%B %Y')} {payment_type} confirmed paid",
            notes=MARKER,
        )


def clear_july_payments(Payment, resident, payment_type):
    Payment.objects.filter(
        application_id=resident.id,
        payment_type=payment_type,
        status="completed",
    ).filter(month_payment_query(JULY)).update(status="failed")


def reconcile_roster_room(CurrentResidentRosterEntry, resident, first_name, last_name, room):
    entries = CurrentResidentRosterEntry.objects.filter(
        property_id=resident.property_id,
        first_name__iexact=first_name,
        last_name__iexact=last_name,
    )
    target = entries.filter(
        Q(room_unit_label__iexact=room) | Q(room_unit_label__iexact=f"Room {room}")
    ).order_by("-id").first()
    if target:
        target.room_unit_label = room
        target.is_active = True
        target.save(update_fields=["room_unit_label", "is_active"])
        entries.exclude(id=target.id).update(is_active=False)
        return

    source = entries.order_by("-id").first()
    if source:
        source.room_unit_label = room
        source.is_active = True
        source.save(update_fields=["room_unit_label", "is_active"])


def reconcile_july_rent_roll(apps, schema_editor):
    HousingApplication = apps.get_model("main", "HousingApplication")
    Payment = apps.get_model("main", "Payment")
    PropertyRoomRent = apps.get_model("main", "PropertyRoomRent")
    RentHistory = apps.get_model("main", "RentHistory")
    RentRollSnapshot = apps.get_model("main", "RentRollSnapshot")
    CurrentResidentRosterEntry = apps.get_model("main", "CurrentResidentRosterEntry")

    resident_specs = (
        ("Robert Cisneros", "P", None, "paid"),
        ("Ron Rucker", "D", None, "paid"),
        ("Ray Ferro", "O", None, "paid"),
        ("Chris Honey", "Q", Decimal("600.00"), "rent_only"),
        ("Mike Dudley", "I", None, "paid"),
        ("Carlos Rios", "F", None, "paid"),
        ("Aaron Brown", "N", Decimal("650.00"), "aaron_due"),
    )

    # Remove the owner from both current and historical resident rolls.
    for owner_record in HousingApplication.objects.filter(full_name__iexact="Mike Bowling"):
        owner_record.space_label = ""
        owner_record.tenancy_status = "former"
        owner_record.application_folder = "archived"
        owner_record.save(update_fields=["space_label", "tenancy_status", "application_folder"])
    CurrentResidentRosterEntry.objects.filter(
        first_name__iexact="Mike", last_name__iexact="Bowling"
    ).update(is_active=False)
    RentRollSnapshot.objects.filter(service_month=JULY, resident_name__iexact="Mike Bowling").delete()

    for name, room, forced_rent, payment_state in resident_specs:
        resident = resident_for_name(HousingApplication, name)
        if not resident:
            # Production data sometimes stores Aaron's middle name.
            if name == "Aaron Brown":
                resident = resident_for_name(HousingApplication, "Aaron Brian Brown")
            elif name == "Ron Rucker":
                resident = resident_for_name(HousingApplication, "Ron Recker")
            if not resident:
                continue

        rent = forced_rent or room_amount(PropertyRoomRent, resident, room, "monthly_rent", Decimal("0.00"))
        utilities = room_amount(PropertyRoomRent, resident, room, "utility_monthly", Decimal("55.00"))

        resident.space_type = "Room"
        resident.space_label = room
        resident.monthly_rent = rent
        resident.utility_monthly = utilities
        snapshot_deposit_paid = resident.deposit_paid
        update_fields = ["space_type", "space_label", "monthly_rent", "utility_monthly"]

        roster_name = resident.full_name.split()
        if len(roster_name) >= 2 and name != "Robert Cisneros":
            reconcile_roster_room(
                CurrentResidentRosterEntry,
                resident,
                roster_name[0],
                roster_name[-1],
                room,
            )

        if name == "Robert Cisneros":
            resident.tenancy_status = "former"
            resident.application_folder = "archived"
            if not resident.move_out_date or resident.move_out_date.year != 2026 or resident.move_out_date.month != 7:
                # Use the accounting month end only when the exact July date
                # was not already recorded in the resident file.
                resident.move_out_date = date(2026, 7, 31)
            resident.tenancy_end_reason = "Resident passed away during July 2026"
            resident.former_tenant_archived_at = timezone.now()
            resident.balance = Decimal("0.00")
            resident.utility_balance = Decimal("0.00")
            update_fields.extend([
                "tenancy_status", "application_folder", "move_out_date", "tenancy_end_reason",
                "former_tenant_archived_at", "balance", "utility_balance",
            ])
            CurrentResidentRosterEntry.objects.filter(
                property_id=resident.property_id,
                first_name__iexact="Robert",
                last_name__iexact="Cisneros",
            ).update(is_active=False)

        if name == "Ron Rucker":
            resident.deposit_required = max(resident.deposit_required or Decimal("0.00"), Decimal("450.00"))
            resident.deposit_paid = Decimal("450.00")
            snapshot_deposit_paid = Decimal("0.00")
            update_fields.extend(["deposit_required", "deposit_paid"])

        resident.save(update_fields=update_fields)
        RentHistory.objects.update_or_create(
            application_id=resident.id,
            effective_date=JULY,
            defaults={"rent_amount": rent},
        )

        if payment_state == "paid":
            ensure_payment(Payment, resident, "rent", rent)
            ensure_payment(Payment, resident, "utility", utilities)
            if name == "Ray Ferro":
                ensure_payment(Payment, resident, "rent", rent, AUGUST)
                ensure_payment(Payment, resident, "utility", utilities, AUGUST)
            elif name == "Ron Rucker":
                ensure_payment(Payment, resident, "deposit", Decimal("450.00"), AUGUST)
        elif payment_state == "rent_only":
            ensure_payment(Payment, resident, "rent", rent)
            clear_july_payments(Payment, resident, "utility")
            resident.utility_balance = max(resident.utility_balance or Decimal("0.00"), utilities)
            resident.save(update_fields=["utility_balance"])
        else:
            clear_july_payments(Payment, resident, "rent")
            clear_july_payments(Payment, resident, "utility")
            ensure_payment(Payment, resident, "rent", Decimal("50.00"))
            resident.balance = max(resident.balance or Decimal("0.00"), Decimal("600.00"))
            resident.utility_balance = max(resident.utility_balance or Decimal("0.00"), utilities)
            resident.save(update_fields=["balance", "utility_balance"])

        RentRollSnapshot.objects.filter(
            property_id=resident.property_id,
            service_month=JULY,
        ).filter(
            Q(application_id=resident.id)
            | Q(room_unit_label__iexact=room)
            | Q(room_unit_label__iexact=f"Room {room}")
            | Q(resident_name__iexact=name)
        ).delete()
        RentRollSnapshot.objects.create(
            property_id=resident.property_id,
            application_id=resident.id,
            service_month=JULY,
            room_unit_label=room,
            resident_name=resident.full_name,
            monthly_rent=rent,
            rent_charge=rent,
            utility_monthly=utilities,
            utility_charge=utilities,
            deposit_required=resident.deposit_required,
            deposit_paid=snapshot_deposit_paid,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("main", "0055_reconcile_michael_mcguffey_july_payments")]

    operations = [migrations.RunPython(reconcile_july_rent_roll, noop_reverse)]
