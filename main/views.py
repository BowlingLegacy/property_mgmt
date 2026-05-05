from collections import OrderedDict
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .forms import BlogCommentForm, HousingApplicationForm
from .models import Property, BlogPost, HousingApplication, Payment


LATE_FEE_AMOUNT = Decimal("25.00")


def home(request):
    properties = Property.objects.all()
    posts = BlogPost.objects.all().order_by("-created_at")[:5]

    return render(request, "home.html", {
        "properties": properties,
        "posts": posts,
    })


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")


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

    return render(request, "apply.html", {"form": form})


def apply_success(request):
    return render(request, "apply_success.html")


def enter_invite_code(request):
    return render(request, "enter_invite_code.html")


def signup(request):
    return render(request, "signup.html")


@login_required
def tenant_dashboard(request):
    request.session.set_expiry(0)

    application = HousingApplication.objects.filter(
        email=request.user.email
    ).first()

    payments = []
    if application:
        payments = application.payments.all().order_by("-created_at")

    return render(request, "tenant_dashboard.html", {
        "application": application,
        "payments": payments,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    })


@login_required
def landlord_dashboard(request):
    applications = HousingApplication.objects.all().order_by("-created_at")
    properties = Property.objects.all()
    payments = Payment.objects.all().order_by("-created_at")[:25]

    return render(request, "landlord_dashboard.html", {
        "applications": applications,
        "properties": properties,
        "payments": payments,
    })


def staff_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


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
        property_name = "No Property Assigned"

        if application.property:
            property_name = application.property.name

        month_label = timezone.localtime(payment.created_at).strftime("%B %Y")

        if property_name not in grouped:
            grouped[property_name] = OrderedDict()

        if month_label not in grouped[property_name]:
            grouped[property_name][month_label] = []

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


def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)

    return render(request, "property_detail.html", {
        "property": property_obj,
    })


def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)

    gallery_images = property_obj.images.all()  # ← THIS FIXES GALLERY

    return render(request, "property_detail.html", {
        "property": property_obj,
        "gallery_images": gallery_images,
    })


def add_blog_comment(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)

    if request.method == "POST":
        form = BlogCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.approved = False
            comment.save()

    return redirect("home")


def printable_application(request, pk):
    application = get_object_or_404(HousingApplication, pk=pk)

    return render(request, "printable_application.html", {
        "application": application,
    })


@login_required
def create_checkout_session(request, application_id, payment_type="rent"):
    application = get_object_or_404(HousingApplication, id=application_id)

    today = timezone.localdate()
    amount = Decimal("0.00")
    description = ""

    if payment_type == "rent":
        base_rent_amount = application.balance if application.balance > 0 else application.monthly_rent
        amount = base_rent_amount
        description = "Rent Payment"

        if today.day >= 5 and base_rent_amount > 0:
            late_fee_already_paid = Payment.objects.filter(
                application=application,
                payment_type="rent",
                description__icontains="late fee",
                status="completed",
                created_at__month=today.month,
                created_at__year=today.year,
            ).exists()

            if not late_fee_already_paid:
                amount = base_rent_amount + LATE_FEE_AMOUNT
                description = "Rent Payment including $25 late fee"

    elif payment_type == "deposit":
        amount = application.deposit_required - application.deposit_paid
        amount = max(amount, Decimal("0.00"))
        description = "Deposit Payment"

    elif payment_type == "utility":
        amount = application.utility_balance if application.utility_balance > 0 else application.utility_monthly
        description = "Shared Utilities Payment"

    else:
        return JsonResponse({"error": "Invalid payment type."}, status=400)

    if amount <= 0:
        return JsonResponse({"error": "No balance due for this payment type."}, status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    payment = Payment.objects.create(
        application=application,
        payment_type=payment_type,
        description=description,
        amount=amount,
        status="pending",
    )

    domain = request.build_absolute_uri("/").rstrip("/")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"{description} - {application.full_name}",
                },
                "unit_amount": int(amount * 100),
            },
            "quantity": 1,
        }],
        success_url=f"{domain}/payment-success/",
        cancel_url=f"{domain}/tenant-dashboard/",
        metadata={
            "payment_id": str(payment.id),
            "application_id": str(application.id),
            "payment_type": payment_type,
        },
    )

    payment.stripe_session_id = session.id
    payment.save()

    return JsonResponse({"id": session.id})


def payment_success(request):
    return render(request, "payment_success.html")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception:
        return HttpResponse(status=400)

    if event["type"] != "checkout.session.completed":
        return HttpResponse(status=200)

    session = event["data"]["object"]

    metadata = session["metadata"] if "metadata" in session else {}
    payment_id = metadata["payment_id"] if "payment_id" in metadata else None

    if not payment_id:
        return HttpResponse(status=200)

    payment = Payment.objects.filter(id=payment_id).first()
    if not payment or payment.status == "completed":
        return HttpResponse(status=200)

    application = payment.application

    payment.status = "completed"
    payment.stripe_payment_intent = session["payment_intent"] if "payment_intent" in session else ""
    payment.save()

    if payment.payment_type == "rent":
        rent_amount = payment.amount

        if "late fee" in payment.description.lower():
            rent_amount = max(Decimal("0.00"), payment.amount - LATE_FEE_AMOUNT)

        application.balance = max(Decimal("0.00"), application.balance - rent_amount)

    elif payment.payment_type == "deposit":
        application.deposit_paid = min(
            application.deposit_required,
            application.deposit_paid + payment.amount
        )

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
Payment received from {application.full_name}

Type: {payment.get_payment_type_display()}
Amount: ${payment.amount}

Rent Balance: ${application.balance}
Deposit Paid: ${application.deposit_paid}
Utilities Balance: ${application.utility_balance}
""",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[owner_email],
        fail_silently=True,
    )

    return HttpResponse(status=200)
