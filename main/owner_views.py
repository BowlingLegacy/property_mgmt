from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    OwnerFinancialUploadForm,
    OwnerLandlordInviteForm,
    OwnerPropertyForm,
    OwnerPropertyOnboardingDocumentsForm,
)
from .invite_utils import create_pending_portal_user, send_portal_access_invite_email
from .models import FinancialEntry, FinancialUpload, Property, PropertyImage, PropertyRoomRent, HousingApplication, Payment, ResidentMessage
from .permissions import can_access_owner_dashboard, is_super_admin, is_assistant_admin
from .views import normalized_room_label, payment_amount_for_month


def owner_dashboard_report_url(report_type, property_obj, extra_params=None):
    params = {
        "report_type": report_type,
        "property_id": property_obj.id,
    }
    if extra_params:
        params.update(extra_params)
    return f"/custom-reports/?{urlencode(params, doseq=True)}"


def owner_dashboard_active_residents(property_obj):
    return (
        HousingApplication.objects
        .filter(property=property_obj, application_folder="active", tenancy_status="active")
        .filter(Q(user__isnull=False) | Q(landlord_reviewed_at__isnull=False))
        .exclude(space_label="")
        .select_related("property")
        .order_by("space_label", "full_name")
    )


def financial_entry_total(property_obj, year, entry_types):
    return (
        FinancialEntry.objects
        .filter(property_name__iexact=property_obj.name, year=year, entry_type__in=entry_types)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )


@login_required
@user_passes_test(can_access_owner_dashboard)
def property_owner_dashboard(request):
    properties = owner_properties_for(request.user)
    today = timezone.localdate()
    selected_month = today.replace(day=1)
    current_year = today.year

    property_cards = []
    portfolio_monthly_rent = Decimal("0.00")
    portfolio_balances_due = Decimal("0.00")
    portfolio_utilities_due = Decimal("0.00")
    portfolio_deposits_held = Decimal("0.00")
    portfolio_rent_collected_month = Decimal("0.00")
    portfolio_rent_collected_ytd = Decimal("0.00")
    total_residents = 0
    total_occupied_units = 0
    total_open_messages = 0

    for property_obj in properties:
        residents = owner_dashboard_active_residents(property_obj)
        resident_count = residents.count()
        open_messages = ResidentMessage.objects.filter(application__property=property_obj, status="submitted").count()
        completed_payments = Payment.objects.filter(application__property=property_obj, status="completed")
        completed_rent_payments = completed_payments.filter(payment_type="rent")

        active_room_settings = PropertyRoomRent.objects.filter(property=property_obj, is_active=True)
        scheduled_rent = active_room_settings.aggregate(total=Sum("monthly_rent"))["total"] or Decimal("0.00")
        if scheduled_rent <= 0:
            scheduled_rent = residents.aggregate(total=Sum("monthly_rent"))["total"] or Decimal("0.00")

        occupied_unit_labels = {
            normalized_room_label(resident.space_label)
            for resident in residents
            if normalized_room_label(resident.space_label)
        }
        occupied_unit_count = len(occupied_unit_labels)

        balances_due = residents.aggregate(total=Sum("balance"))["total"] or Decimal("0.00")
        utilities_due = residents.aggregate(total=Sum("utility_balance"))["total"] or Decimal("0.00")
        deposits_held = residents.aggregate(total=Sum("deposit_paid"))["total"] or Decimal("0.00")
        rent_collected_month = payment_amount_for_month(completed_rent_payments, selected_month.year, selected_month.month, ["rent"])
        rent_collected_ytd = sum(
            payment_amount_for_month(completed_rent_payments, current_year, month_number, ["rent"])
            for month_number in range(1, today.month + 1)
        )
        operating_expenses_ytd = financial_entry_total(property_obj, current_year, ["operating_expense"])
        debt_service_ytd = financial_entry_total(property_obj, current_year, ["debt_service"])
        capital_expenses_ytd = financial_entry_total(property_obj, current_year, ["capital_expense"])
        income_ytd = financial_entry_total(property_obj, current_year, ["income"])
        noi_ytd = income_ytd - operating_expenses_ytd
        cash_flow_ytd = noi_ytd - debt_service_ytd

        portfolio_monthly_rent += scheduled_rent
        portfolio_balances_due += balances_due
        portfolio_utilities_due += utilities_due
        portfolio_deposits_held += deposits_held
        portfolio_rent_collected_month += rent_collected_month
        portfolio_rent_collected_ytd += rent_collected_ytd
        total_residents += resident_count
        total_occupied_units += occupied_unit_count
        total_open_messages += open_messages

        property_cards.append({
            "property": property_obj,
            "resident_count": resident_count,
            "occupied_unit_count": occupied_unit_count,
            "monthly_rent": scheduled_rent,
            "balances_due": balances_due,
            "utilities_due": utilities_due,
            "deposits_held": deposits_held,
            "rent_collected_month": rent_collected_month,
            "rent_collected_ytd": rent_collected_ytd,
            "operating_expenses_ytd": operating_expenses_ytd,
            "debt_service_ytd": debt_service_ytd,
            "capital_expenses_ytd": capital_expenses_ytd,
            "noi_ytd": noi_ytd,
            "cash_flow_ytd": cash_flow_ytd,
            "open_messages": open_messages,
            "links": {
                "resident_roster": owner_dashboard_report_url("resident_roster", property_obj),
                "rent_roll": f"/rent-roll/?property_id={property_obj.id}&month={selected_month:%Y-%m}",
                "payment_summary": owner_dashboard_report_url("payment_summary", property_obj, {
                    "start_date": selected_month.isoformat(),
                    "end_date": today.isoformat(),
                }),
                "operating_expenses": owner_dashboard_report_url("financial_entries", property_obj, {
                    "financial_entry_types": ["operating_expense"],
                }),
                "debt_service": owner_dashboard_report_url("financial_entries", property_obj, {
                    "financial_entry_types": ["debt_service"],
                }),
                "capital_expenses": owner_dashboard_report_url("financial_entries", property_obj, {
                    "financial_entry_types": ["capital_expense"],
                }),
                "noi": f"/t12-report/?property_id={property_obj.id}&year={current_year}",
                "cash_flow": f"/t12-report/?property_id={property_obj.id}&year={current_year}",
                "occupancy": owner_dashboard_report_url("occupancy_vacancy", property_obj),
            },
        })

    recent_messages = ResidentMessage.objects.filter(
        application__property__in=properties
    ).select_related(
        "application", "application__property"
    ).order_by("-created_at")[:12]

    return render(request, "property_owner_dashboard.html", {
        "property_cards": property_cards,
        "properties": properties,
        "total_properties": properties.count(),
        "total_residents": total_residents,
        "total_occupied_units": total_occupied_units,
        "portfolio_monthly_rent": portfolio_monthly_rent,
        "portfolio_balances_due": portfolio_balances_due,
        "portfolio_utilities_due": portfolio_utilities_due,
        "portfolio_deposits_held": portfolio_deposits_held,
        "portfolio_rent_collected_month": portfolio_rent_collected_month,
        "portfolio_rent_collected_ytd": portfolio_rent_collected_ytd,
        "total_open_messages": total_open_messages,
        "recent_messages": recent_messages,
        "selected_month": selected_month,
        "current_year": current_year,
    })


def owner_properties_for(user):
    if is_super_admin(user) or is_assistant_admin(user):
        return Property.objects.all().order_by("name")

    return Property.objects.filter(owner_email__iexact=user.email).order_by("name")


@login_required
@user_passes_test(can_access_owner_dashboard)
def owner_property_create(request):
    form = OwnerPropertyForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        property_obj = form.save(commit=False)
        property_obj.owner_email = request.user.email
        property_obj.save()

        PropertyImage.objects.bulk_create([
            PropertyImage(property=property_obj, image=image)
            for image in form.cleaned_data["gallery_images"]
        ])
        form.save_utility_vendors(property_obj)

        messages.success(request, f"{property_obj.name} was added to your owner dashboard.")
        return redirect("owner_property_onboarding_documents", property_id=property_obj.id)

    return render(request, "owner_property_form.html", {"form": form})


@login_required
@user_passes_test(can_access_owner_dashboard)
def owner_property_onboarding_documents(request, property_id):
    property_obj = get_object_or_404(owner_properties_for(request.user), id=property_id)
    form = OwnerPropertyOnboardingDocumentsForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save(property_obj)
        messages.success(
            request,
            "Property onboarding files were saved for conversion and property setup review.",
        )
        return redirect("property_owner_dashboard")

    documents = property_obj.onboarding_documents.all()
    return render(request, "owner_property_onboarding_documents.html", {
        "form": form,
        "property": property_obj,
        "documents": documents,
    })


@login_required
@user_passes_test(can_access_owner_dashboard)
def owner_landlord_invite(request):
    properties = owner_properties_for(request.user)
    form = OwnerLandlordInviteForm(request.POST or None, properties=properties)

    if request.method == "POST" and form.is_valid():
        intake = form.save()
        property_obj = form.cleaned_data["property"]
        property_obj.landlord_email = intake.email
        property_obj.save(update_fields=["landlord_email"])

        user = create_pending_portal_user(intake.full_name, intake.email, "landlord", intake.id)
        user.refresh_invite_code()
        intake.user = user
        intake.status = "invited"
        intake.invite_sent_at = timezone.now()
        intake.save(update_fields=["user", "status", "invite_sent_at"])

        try:
            send_portal_access_invite_email(user, intake.full_name, "Landlord")
        except Exception as exc:
            messages.warning(request, f"Landlord setup code created, but email failed: {exc}")
        else:
            messages.success(request, "Landlord setup invite email sent.")

        messages.info(request, f"Backup landlord setup code: {user.invite_code}")
        return redirect("property_owner_dashboard")

    return render(request, "owner_landlord_invite.html", {
        "form": form,
        "properties": properties,
    })


@login_required
@user_passes_test(can_access_owner_dashboard)
def owner_financial_upload(request):
    properties = owner_properties_for(request.user)
    form = OwnerFinancialUploadForm(request.POST or None, request.FILES or None, properties=properties)

    if request.method == "POST" and form.is_valid():
        upload = form.save()
        messages.success(request, "Financial document uploaded for review and import processing.")
        return redirect("owner_financial_upload")

    uploads = FinancialUpload.objects.filter(property__in=properties).select_related("property").order_by("-uploaded_at")
    return render(request, "owner_financial_upload.html", {
        "form": form,
        "uploads": uploads,
        "properties": properties,
    })
