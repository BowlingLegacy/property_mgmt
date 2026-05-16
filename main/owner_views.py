from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.shortcuts import render

from .models import Property, HousingApplication, Payment, ResidentMessage
from .views import staff_required


@login_required
@user_passes_test(staff_required)
def property_owner_dashboard(request):
    if request.user.is_superuser or getattr(request.user, "role", "") == "admin":
        properties = Property.objects.all().order_by("name")
    else:
        properties = Property.objects.filter(owner_email__iexact=request.user.email).order_by("name")

    property_cards = []
    portfolio_monthly_rent = Decimal("0.00")
    portfolio_balances_due = Decimal("0.00")
    portfolio_utilities_due = Decimal("0.00")
    portfolio_deposits_held = Decimal("0.00")
    portfolio_collected = Decimal("0.00")
    total_residents = 0
    total_open_messages = 0

    for property_obj in properties:
        residents = HousingApplication.objects.filter(property=property_obj).order_by("space_label", "full_name")
        resident_count = residents.count()
        open_messages = ResidentMessage.objects.filter(application__property=property_obj, status="submitted").count()
        completed_payments = Payment.objects.filter(application__property=property_obj, status="completed")

        monthly_rent = residents.aggregate(total=Sum("monthly_rent"))["total"] or Decimal("0.00")
        balances_due = residents.aggregate(total=Sum("balance"))["total"] or Decimal("0.00")
        utilities_due = residents.aggregate(total=Sum("utility_balance"))["total"] or Decimal("0.00")
        deposits_held = residents.aggregate(total=Sum("deposit_paid"))["total"] or Decimal("0.00")
        total_collected = completed_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        portfolio_monthly_rent += monthly_rent
        portfolio_balances_due += balances_due
        portfolio_utilities_due += utilities_due
        portfolio_deposits_held += deposits_held
        portfolio_collected += total_collected
        total_residents += resident_count
        total_open_messages += open_messages

        property_cards.append({
            "property": property_obj,
            "resident_count": resident_count,
            "monthly_rent": monthly_rent,
            "balances_due": balances_due,
            "utilities_due": utilities_due,
            "deposits_held": deposits_held,
            "total_collected": total_collected,
            "open_messages": open_messages,
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
        "portfolio_monthly_rent": portfolio_monthly_rent,
        "portfolio_balances_due": portfolio_balances_due,
        "portfolio_utilities_due": portfolio_utilities_due,
        "portfolio_deposits_held": portfolio_deposits_held,
        "portfolio_collected": portfolio_collected,
        "total_open_messages": total_open_messages,
        "recent_messages": recent_messages,
    })
