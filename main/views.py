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

            user_with_code = User.objects.filter(
                invite_code=code
            ).first()

            if not user_with_code:
                messages.error(request, "Invalid access code.")
                return redirect("enter_invite_code")

            profile = HousingApplication.objects.filter(
                user=user_with_code
            ).first()

            if not profile:
                profile = HousingApplication.objects.filter(
                    email=user_with_code.email
                ).first()

            if not profile:
                messages.error(
                    request,
                    "No resident file is connected to this code yet."
                )
                return redirect("enter_invite_code")

            profile.user = request.user
            profile.save()

            messages.success(
                request,
                "Resident file linked successfully."
            )

            return redirect("tenant_dashboard")

    return render(request, "enter_invite_code.html", {
        "form": form,
    })


# =========================================================
# TENANT DASHBOARD = RESIDENT FILE
# =========================================================

@login_required
def tenant_dashboard(request):

    request.session.set_expiry(0)

    application = getattr(
        request.user,
        "resident_profile",
        None
    )

    payments = []

    if application:
        payments = application.payments.all().order_by("-created_at")

    return render(request, "tenant_dashboard.html", {
        "application": application,
        "payments": payments,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    })


# =========================================================
# LANDLORD DASHBOARD
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

        property_name = (
            application.property.name
            if application.property
            else "No Property"
        )

        month_label = timezone.localtime(
            payment.created_at
        ).strftime("%B %Y")

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
                    (
                        p.application.space_label
                        or p.application.space_type
                        or ""
                    ).lower(),
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
        .order_by(
            "property__name",
            "space_label",
            "full_name"
        )
    )

    rows = []

    for resident in residents:

        completed_payments = resident.payments.filter(
            status="completed"
        )

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
@login_required
@user_passes_test(staff_required)
def export_payment_log_csv(request):

    response = HttpResponse(content_type="text/csv")

    response["Content-Disposition"] = (
        'attachment; filename="payment_log.csv"'
    )

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
            payment.application.property.name
            if payment.application.property else "",
            payment.get_payment_type_display(),
            payment.amount,
            payment.status,
            timezone.localtime(payment.created_at).strftime(
                "%Y-%m-%d %H:%M"
            ),
        ])

    return response


@login_required
@user_passes_test(staff_required)
def export_rent_roll_csv(request):

    response = HttpResponse(content_type="text/csv")

    response["Content-Disposition"] = (
        'attachment; filename="rent_roll.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "Resident",
        "Property",
        "Room",
        "Monthly Rent",
        "Balance",
        "Deposit Required",
        "Deposit Paid",
        "Utility Balance",
    ])

    residents = HousingApplication.objects.all()

    for resident in residents:

        writer.writerow([
            resident.full_name,
            resident.property.name if resident.property else "",
            resident.space_label,
            resident.monthly_rent,
            resident.balance,
            resident.deposit_required,
            resident.deposit_paid,
            resident.utility_balance,
        ])

    return response


@login_required
@user_passes_test(staff_required)
def export_t12_csv(request):

    response = HttpResponse(content_type="text/csv")

    response["Content-Disposition"] = (
        'attachment; filename="t12_report.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "Month",
        "Income",
        "Expenses",
        "Debt Service",
        "Cash Flow",
    ])

    current_year = timezone.localdate().year

    for month in range(1, 13):

        income = (
            Payment.objects.filter(
                status="completed",
                created_at__year=current_year,
                created_at__month=month,
            ).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        expenses = (
            FinancialEntry.objects.filter(
                year=current_year,
                month=month,
                entry_type="operating_expense",
            ).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        debt_service = (
            FinancialEntry.objects.filter(
                year=current_year,
                month=month,
                entry_type="debt_service",
            ).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        cash_flow = income - expenses - debt_service

        writer.writerow([
            date(current_year, month, 1).strftime("%B"),
            income,
            expenses,
            debt_service,
            cash_flow,
        ])

    return response

# =========================================================
# T12 REPORT
# =========================================================

@login_required
@user_passes_test(staff_required)
def t12_report(request):

    year = timezone.localdate().year

    financial_entries = FinancialEntry.objects.filter(
        year=year
    )

    months = []

    for month_number in range(1, 13):

        online_income = (
            Payment.objects
            .filter(
                status="completed",
                created_at__year=year,
                created_at__month=month_number,
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        spreadsheet_income = (
            financial_entries
            .filter(
                month=month_number,
                entry_type="income"
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        operating_expenses = (
            financial_entries
            .filter(
                month=month_number,
                entry_type="operating_expense"
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        debt_service = (
            financial_entries
            .filter(
                month=month_number,
                entry_type="debt_service"
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        capital_expenses = (
            financial_entries
            .filter(
                month=month_number,
                entry_type="capital_expense"
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        total_income = online_income + spreadsheet_income
        noi = total_income - operating_expenses
        cash_flow = noi - debt_service

        months.append({
            "month_name": date(year, month_number, 1).strftime("%B"),
            "online_income": online_income,
            "spreadsheet_income": spreadsheet_income,
            "total_income": total_income,
            "operating_expenses": operating_expenses,
            "debt_service": debt_service,
            "capital_expenses": capital_expenses,
            "noi": noi,
            "cash_flow_after_debt": cash_flow,
        })

    return render(request, "t12_report.html", {
        "year": year,
        "months": months,
    })


# =========================================================
# FINANCIAL UPLOADS
# =========================================================

@login_required
@user_passes_test(staff_required)
def financial_upload(request):

    if request.method == "POST":

        form = FinancialUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            upload = form.save()

            return redirect(
                "parse_financial_upload",
                upload_id=upload.id
            )

    else:
        form = FinancialUploadForm()

    uploads = FinancialUpload.objects.all().order_by(
        "-uploaded_at"
    )

    return render(request, "financial_upload.html", {
        "form": form,
        "uploads": uploads,
    })


@login_required
@user_passes_test(staff_required)
def parse_financial_upload(request, upload_id):

    upload = get_object_or_404(
        FinancialUpload,
        id=upload_id
    )

    upload.parsed_at = timezone.now()
    upload.save()

    return render(request, "financial_upload_parsed.html", {
        "upload": upload,
        "created": 0,
    })

@login_required
@user_passes_test(staff_required)
def property_financials(request, property_name):

    property_obj = get_object_or_404(
        Property,
        name=property_name
    )

    residents = HousingApplication.objects.filter(
        property=property_obj
    )

    monthly_rent = sum(
        [r.monthly_rent for r in residents],
        Decimal("0.00")
    )

    balances_due = sum(
        [r.balance for r in residents],
        Decimal("0.00")
    )

    utilities_due = sum(
        [r.utility_balance for r in residents],
        Decimal("0.00")
    )

    deposits_held = sum(
        [r.deposit_paid for r in residents],
        Decimal("0.00")
    )

    completed_payments = Payment.objects.filter(
        application__property=property_obj,
        status="completed"
    )

    total_collected = (
        completed_payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    context = {
        "property": property_obj,
        "residents": residents,
        "monthly_rent": monthly_rent,
        "balances_due": balances_due,
        "utilities_due": utilities_due,
        "deposits_held": deposits_held,
        "total_collected": total_collected,
    }

    return render(
        request,
        "property_financials.html",
        context
    )


# =========================================================
# PROPERTY / BLOG
# =========================================================

def property_detail(request, pk):

    property_obj = get_object_or_404(
        Property,
        pk=pk
    )

    gallery_images = property_obj.images.all()

    return render(request, "property_detail.html", {
        "property": property_obj,
        "gallery_images": gallery_images,
    })


def blog_detail(request, pk):

    post = get_object_or_404(
        BlogPost,
        pk=pk
    )

    return render(request, "blog_detail.html", {
        "post": post,
    })


def add_blog_comment(request, post_id):

    post = get_object_or_404(
        BlogPost,
        id=post_id
    )

    if request.method == "POST":

        form = BlogCommentForm(request.POST)

        if form.is_valid():

            comment = form.save(commit=False)
            comment.post = post
            comment.approved = False
            comment.save()

    return redirect("home")


# =========================================================
# APPLICATION PRINT
# =========================================================

def printable_application(request, pk):

    application = get_object_or_404(
        HousingApplication,
        pk=pk
    )

    return render(request, "printable_application.html", {
        "application": application,
    })


# =========================================================
# STRIPE PAYMENTS
# =========================================================

@login_required
def create_checkout_session(
    request,
    application_id,
    payment_type="rent"
):

    application = get_object_or_404(
        HousingApplication,
        id=application_id
    )

    amount = Decimal("0.00")
    description = ""

    if payment_type == "rent":

        amount = (
            application.balance
            if application.balance > 0
            else application.monthly_rent
        )

        description = "Rent Payment"

    elif payment_type == "deposit":

        amount = max(
            application.deposit_required - application.deposit_paid,
            Decimal("0.00")
        )

        description = "Deposit Payment"

    elif payment_type == "utility":

        amount = (
            application.utility_balance
            if application.utility_balance > 0
            else application.utility_monthly
        )

        description = "Utility Payment"

    else:
        return JsonResponse({
            "error": "Invalid payment type"
        })

    if amount <= 0:
        return JsonResponse({
            "error": "No balance due"
        })

    payment = Payment.objects.create(
        application=application,
        payment_type=payment_type,
        description=description,
        amount=amount,
        status="pending",
    )

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",

        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": description
                },
                "unit_amount": int(amount * 100),
            },
            "quantity": 1,
        }],

        success_url=request.build_absolute_uri(
            "/payment-success/"
        ),

        cancel_url=request.build_absolute_uri(
            "/tenant-dashboard/"
        ),

        metadata={
            "payment_id": str(payment.id)
        },
    )

    payment.stripe_session_id = session.id
    payment.save()

    return redirect(session.url)


def payment_success(request):
    return render(request, "payment_success.html")


# =========================================================
# STRIPE WEBHOOK
# =========================================================

@csrf_exempt
def stripe_webhook(request):

    payload = request.body

    sig_header = request.META.get(
        "HTTP_STRIPE_SIGNATURE"
    )

    try:

        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )

    except Exception:
        return HttpResponse(status=400)

    if event["type"] != "checkout.session.completed":
        return HttpResponse(status=200)

    session = event["data"]["object"]

    payment_id = session.get(
        "metadata",
        {}
    ).get("payment_id")

    if not payment_id:
        return HttpResponse(status=200)

    payment = Payment.objects.filter(
        id=payment_id
    ).first()

    if not payment:
        return HttpResponse(status=200)

    if payment.status == "completed":
        return HttpResponse(status=200)

    payment.status = "completed"
    payment.stripe_payment_intent = session.get(
        "payment_intent",
        ""
    )

    payment.save()

    application = payment.application

    if payment.payment_type == "rent":

        application.balance = max(
            Decimal("0.00"),
            application.balance - payment.amount
        )

    elif payment.payment_type == "deposit":

        application.deposit_paid += payment.amount

    elif payment.payment_type == "utility":

        application.utility_balance = max(
            Decimal("0.00"),
            application.utility_balance - payment.amount
        )

    application.save()

    owner_email = "BowlingLegacyLLC@outlook.com"

    if application.property and application.property.owner_email:
        owner_email = application.property.owner_email

    send_mail(
        subject="Resident Payment Received",

        message=f"""
Resident: {application.full_name}

Payment Type:
{payment.get_payment_type_display()}

Amount:
${payment.amount}
""",

        from_email=getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            None
        ),

        recipient_list=[owner_email],

        fail_silently=True,
    )

    return HttpResponse(status=200)
