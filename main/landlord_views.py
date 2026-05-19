from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LandlordCreateTenantForm
from .models import HousingApplication
from .views import staff_required


@login_required
@user_passes_test(staff_required)
def create_tenant(request):
    application_id = request.GET.get("application")

    application = get_object_or_404(
        HousingApplication,
        id=application_id,
    )

    if request.method == "POST":
        form = LandlordCreateTenantForm(request.POST)

        if form.is_valid():
            application.space_type = form.cleaned_data.get("space_type", "")
            application.space_label = form.cleaned_data.get("space_label", "")
            application.monthly_rent = form.cleaned_data.get("monthly_rent") or 0
            application.balance = form.cleaned_data.get("balance") or 0
            application.rent_due_day = form.cleaned_data.get("rent_due_day") or 1
            application.lease_start_date = form.cleaned_data.get("lease_start_date")
            application.deposit_required = form.cleaned_data.get("deposit_required") or 0
            application.deposit_paid = form.cleaned_data.get("deposit_paid") or 0
            application.utility_monthly = form.cleaned_data.get("utility_monthly") or 0
            application.utility_balance = form.cleaned_data.get("utility_balance") or 0
            application.additional_notes = form.cleaned_data.get("additional_notes") or ""

            application.save()

            messages.success(request, "Application approved and resident onboarding initialized.")

            return render(request, "landlord_create_tenant_success.html", {
                "application": application,
            })

    else:
        form = LandlordCreateTenantForm(initial={
            "monthly_rent": application.monthly_rent,
            "balance": application.balance,
            "deposit_required": application.deposit_required,
            "deposit_paid": application.deposit_paid,
    })
