from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .forms import LandlordCreateTenantForm
from .models import HousingApplication, User
from .views import staff_required


@login_required
@user_passes_test(staff_required)
def create_tenant(request):
    if request.method == "POST":
        form = LandlordCreateTenantForm(request.POST)

        if form.is_valid():
            created_user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data.get("email", ""),
                password=form.cleaned_data["temporary_password"],
                role="tenant",
                is_staff=False,
                is_superuser=False,
            )

            created_application = HousingApplication.objects.create(
                user=created_user,
                property=form.cleaned_data.get("property"),
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data.get("phone", ""),
                email=form.cleaned_data.get("email", ""),
                age=form.cleaned_data.get("age") or 0,
                space_type=form.cleaned_data.get("space_type", ""),
                space_label=form.cleaned_data.get("space_label", ""),
                monthly_rent=form.cleaned_data.get("monthly_rent") or 0,
                balance=form.cleaned_data.get("balance") or 0,
                rent_due_day=form.cleaned_data.get("rent_due_day") or 1,
                lease_start_date=form.cleaned_data.get("lease_start_date"),
                deposit_required=form.cleaned_data.get("deposit_required") or 0,
                deposit_paid=form.cleaned_data.get("deposit_paid") or 0,
                utility_monthly=form.cleaned_data.get("utility_monthly") or 0,
                utility_balance=form.cleaned_data.get("utility_balance") or 0,
                income_source=form.cleaned_data.get("income_source") or "Not entered by landlord",
                monthly_income=form.cleaned_data.get("monthly_income") or 0,
                housing_need=form.cleaned_data.get("housing_need") or "Resident created by landlord.",
                additional_notes=form.cleaned_data.get("additional_notes") or "",
            )

            messages.success(request, "Tenant/resident file created successfully.")
            return render(request, "landlord_create_tenant_success.html", {
                "created_user": created_user,
                "created_application": created_application,
                "temporary_password": form.cleaned_data["temporary_password"],
            })
    else:
        form = LandlordCreateTenantForm()

    return render(request, "landlord_create_tenant.html", {"form": form})
