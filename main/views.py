import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .forms import BlogCommentForm, HousingApplicationForm
from .models import Property, BlogPost, HousingApplication, Payment


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

    return render(request, "apply.html", {"form": form})


def apply_success(request):
    return render(request, "apply_success.html")


def enter_invite_code(request):
    return render(request, "enter_invite_code.html")


def signup(request):
    return render(request, "signup.html")


@login_required
def tenant_dashboard(request):
    application = HousingApplication.objects.filter(email=request.user.email).first()

    return render(request, "tenant_dashboard.html", {
        "application": application,
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


def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)

    return render(request, "property_detail.html", {
        "property": property_obj,
    })


def blog_detail(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)

    return render(request, "blog_detail.html", {
        "post": post,
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
def create_checkout_session(request, application_id):
    application = get_object_or_404(HousingApplication, id=application_id)

    amount = application.balance if application.balance > 0 else application.monthly_rent

    if amount <= 0:
        return JsonResponse({
            "error": "No rent balance or monthly rent amount is set for this resident."
        }, status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    payment = Payment.objects.create(
        application=application,
        amount=amount,
        status="pending",
    )

    domain = request.build_absolute_uri("/").rstrip("/")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Rent Payment - {application.full_name}",
                    },
                    "unit_amount": int(amount * Decimal("100")),
                },
                "quantity": 1,
            }
        ],
        success_url=f"{domain}/payment-success/",
        cancel_url=f"{domain}/tenant-dashboard/",
        metadata={
            "payment_id": payment.id,
            "application_id": application.id,
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
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            endpoint_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment_id = session.get("metadata", {}).get("payment_id")

        if payment_id:
            payment = Payment.objects.filter(id=payment_id).first()

            if payment and payment.status != "completed":
                payment.status = "completed"
                payment.stripe_payment_intent = session.get("payment_intent", "")
                payment.save()

                application = payment.application
                application.balance = max(
                    Decimal("0.00"),
                    application.balance - payment.amount
                )
                application.save()

    return HttpResponse(status=200)
