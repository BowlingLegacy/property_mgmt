import stripe
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(request, application_id, payment_type="rent"):
    application = get_object_or_404(HousingApplication, id=application_id)

    if payment_type == "rent":
        amount = int(application.balance * 100)
        description = f"Rent Payment - {application.full_name}"

    elif payment_type == "deposit":
        amount = int((application.deposit_required - application.deposit_paid) * 100)
        description = f"Deposit Payment - {application.full_name}"

    elif payment_type == "utility":
        amount = int(application.utility_balance * 100)
        description = f"Utility Payment - {application.full_name}"

    else:
        return redirect("tenant_dashboard")

    if amount <= 0:
        return redirect("tenant_dashboard")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": description,
                },
                "unit_amount": amount,
            },
            "quantity": 1,
        }],
        success_url=request.build_absolute_uri(
            reverse("payment_success")
        ) + f"?application_id={application.id}&type={payment_type}",
        cancel_url=request.build_absolute_uri(
            reverse("tenant_dashboard")
        ),
    )

    return redirect(session.url)
