from collections import OrderedDict
from datetime import date
from decimal import Decimal, InvalidOperation
import csv

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .forms import (
    InviteCodeForm,
    BlogCommentForm,
    HousingApplicationForm,
    FinancialUploadForm,
)

from .models import (
    User,
    Property,
    BlogPost,
    HousingApplication,
    Payment,
    FinancialUpload,
    FinancialEntry,
    ResidentMessage,
)

stripe.api_key = settings.STRIPE_SECRET_KEY

LATE_FEE_AMOUNT = Decimal("25.00")


def money(value):
    if value is None:
        return Decimal("0.00")

    if isinstance(value, Decimal):
        return value

    try:
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def staff_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# =========================================================
# PUBLIC PAGES
# =========================================================

def home(request):
    properties = Property.objects.all()
    posts = BlogPost.objects.all().order_by("-created_at")[:5]

    return render(request, "home.html", {
        "properties": properties,
        "posts": posts,
    })


def creed(request):
    return render(request, "creed.html")


def apply(request):
    if request.method == "POST":
        form = HousingApplicationForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect("apply_success")
    else:
        form = HousingApplicationForm()

    return render(request, "apply.html", {
        "form": form,
    })


def apply_success(request):
    return render(request, "apply_success.html")


# =========================================================
# AUTH
# =========================================================

def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")


def signup(request):
    return render(request, "signup.html")


@login_required
def enter_invite_code(request):
    form = InviteCodeForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            code = form.cleaned_data["invite_code"].upper()

            user_with_code = User.objects.filter(invite_code=code).first()

            if not user_with_code:
                messages.error(request, "Invalid access code.")
                return redirect("enter_invite_code")

            profile = HousingApplication.objects.filter(user=user_with_code).first()

            if not profile:
                profile = HousingApplication.objects.filter(email=user_with_code.email).first()

            if not profile:
                messages.error(request, "No resident file is connected to this code yet.")
                return redirect("enter_invite_code")

            profile.user = request.user
            profile.save()

            messages.success(request, "Resident file linked successfully.")
            return redirect("tenant_dashboard")

    return render(request, "enter_invite_code.html", {
        "form": form,
    })


# =========================================================
# DASHBOARDS
# =========================================================

@login_required
@user_passes_test(staff_required)
def landlord_dashboard(request):
    applications = HousingApplication.objects.all().order_by("-created_at")
    properties = Property.objects.all()
    payments = Payment.objects.all().order_by("-created_at")[:25]

    return render(request, "landlord_dashboard.html", {
        "applications": applications,
        "properties": properties,
        "payments": payments,
    })


@login_required
def tenant_dashboard(request):
    request.session.set_expiry(0)

    application = getattr(request.user, "resident_profile", None)

    payments = []
    resident_messages = []
    total_due = Decimal("0.00")

    if application:
        payments = application.payments.all().order_by("-created_at")
        resident_messages = application.resident_messages.all().order_by("-created_at")

        rent_due = application.balance if application.balance > 0 else Decimal("0.00")
        deposit_due = max(
            application.deposit_required - application.deposit_paid,
            Decimal("0.00")
        )
        utility_due = application.utility_balance if application.utility_balance > 0 else Decimal("0.00")

        total_due = rent_due + deposit_due + utility_due

    return render(request, "tenant_dashboard.html", {
        "application": application,
        "payments": payments,
        "resident_messages": resident_messages,
        "total_due": total_due,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    })


@login_required
def submit_resident_message(request):
    if request.method != "POST":
        return redirect("tenant_dashboard")

    application = getattr(request.user, "resident_profile", None)

    if not application:
        messages.error(request, "No resident file connected.")
        return redirect("tenant_dashboard")

    message_type = request.POST.get("message_type", "general")
    subject = request.POST.get("subject", "").strip()
    message = request.POST.get("message", "").strip()

    if not subject or not message:
        messages.error(request, "Subject and message are required.")
        return redirect("tenant_dashboard")

    ResidentMessage.objects.create(
        application=application,
        message_type=message_type,
        subject=subject,
        message=message,
        status="submitted",
        locked=True,
    )

    messages.success(request, "Your message/request has been submitted.")
    return redirect("tenant_dashboard")


# =========================================================
# PAYMENT LOG
# =========================================================

@login_required
@user_passes_test(staff_required)
def payment_log(request):
    completed_payments = (
        Payment.objects
        .filter(status="completed")
        .select_related("application", "application__property")
        .order_by(
            "application__property__name",
            "-created_at",
            "application__space_label",
            "application__full_name",
        )
    )

    grouped = OrderedDict()

    for payment in completed_payments:
        application = payment.application
        property_name = application.property.name if application.property else "No Property"
        month_label = timezone.localtime(payment.created_at).strftime("%B %Y")

        grouped.setdefault(property_name, OrderedDict())
        grouped[property_name].setdefault(month_label, [])
        grouped[property_name][month_label].append(payment)

    payment_log_data = []

    for property_name, months in grouped.items():
        month_data = []

        for month_label, payments in months.items():
            payments_sorted = sorted(
                payments,
                key=lambda p: (
                    (p.application.space_label or p.application.space_type or "").lower(),
                    p.application.full_name.lower(),
                )
            )

            month_data.append({
                "month_label": month_label,
                "payments": payments_sorted,
            })

        payment_log_data.append({
            "property_name": property_name,
            "months": month_data,
        })

    return render(request, "payment_log.html", {
        "payment_log": payment_log_data,
    })


# =========================================================
# RENT ROLL
# =========================================================

@login_required
@user_passes_test(staff_required)
def rent_roll(request):
    residents = (
        HousingApplication.objects
        .select_related("property")
        .order_by("property__name", "space_label", "full_name")
    )

    rows = []

    for resident in residents:
        completed_payments = resident.payments.filter(status="completed")

        rent_paid = (
            completed_payments
            .filter(payment_type="rent")
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        utility_paid = (
            completed_payments
            .filter(payment_type="utility")
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        rows.append({
            "property": resident.property.name if resident.property else "No Property",
            "room": resident.space_label or resident.space_type or "—",
            "resident": resident.full_name,
            "monthly_rent": resident.monthly_rent,
            "rent_balance": resident.balance,
            "rent_paid": rent_paid,
            "utility_monthly": resident.utility_monthly,
            "utility_balance": resident.utility_balance,
            "utility_paid": utility_paid,
            "deposit_required": resident.deposit_required,
            "deposit_paid": resident.deposit_paid,
        })

    return render(request, "rent_roll.html", {
        "rows": rows,
    })


# =========================================================
# CSV EXPORTS
# =========================================================

@login_required
@user_passes_test(staff_required)
def export_payment_log_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="payment_log.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Resident",
        "Property",
        "Payment Type",
        "Amount",
        "Status",
        "Date",
    ])

    payments = Payment.objects.all().order_by("-created_at")

    for payment in payments:
        writer.writerow([
            payment.application.full_name,
            payment.application.property.name if payment.application.property else "",
            payment.get_payment_type_display(),
            payment.amount,
            payment.status,
            timezone.localtime(payment.created_at).strftime("%Y-%m-%d %H:%M"),
        ])
