from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify

from .forms import LandlordCreateTenantForm
from .models import HousingApplication, SignedDocument, User
from .views import staff_managed_properties, staff_required


def send_resident_invite_email(application):
    if not application.user or not application.user.email:
        return False

    if not application.user.invite_code or application.user.invite_code_used_at:
        application.user.refresh_invite_code()

    send_mail(
        "Your Bowling Legacy Resident Portal Access Code",
        f"""Hello {application.full_name},

Your Bowling Legacy resident portal access code is:

{application.user.invite_code}

Portal setup:
https://bowlinglegacy.com/enter-invite-code/

This code is single-use and expires 30 minutes after it is issued. If it expires, request a new code from the invite-code page.

Thank you,
Bowling Legacy Housing
""",
        getattr(settings, "DEFAULT_FROM_EMAIL", None),
        [application.user.email],
        fail_silently=False,
    )

    return True


def ensure_onboarding_documents(application):
    document_specs = [
        ("lease", "Resident Lease Agreement"),
        ("emergency_contact", "Emergency Contact Sheet"),
        ("painted_lady_acknowledgment", "Who We Are / Painted Lady Acknowledgment"),
    ]

    for document_type, title in document_specs:
        document, _ = SignedDocument.objects.get_or_create(
            application=application,
            document_type=document_type,
            defaults={
                "title": title,
                "lease_sent_date": timezone.localdate(),
                "landlord_name": "Michael Bowling",
                "landlord_signature": "Michael Bowling",
            },
        )

        if not document.locked:
            document.title = title
            document.lease_sent_date = document.lease_sent_date or timezone.localdate()
            document.landlord_name = document.landlord_name or "Michael Bowling"
            document.landlord_signature = document.landlord_signature or "Michael Bowling"
            document.save()


@login_required
@user_passes_test(staff_required)
def create_tenant(request):
    application_id = request.GET.get("application")

    if not application_id:
        messages.warning(request, "Choose an application before creating a resident file.")
        return redirect("landlord_dashboard")

    application = get_object_or_404(
        HousingApplication,
        id=application_id,
    )

    if application.property_id not in set(staff_managed_properties(request.user).values_list("id", flat=True)):
        messages.error(request, "That resident file is not assigned to your property workspace.")
        return redirect("landlord_dashboard")

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
            application.deposit_payment_plan = form.cleaned_data.get("deposit_payment_plan") or "paid_in_full"
            application.utility_monthly = form.cleaned_data.get("utility_monthly") or 0
            application.utility_balance = form.cleaned_data.get("utility_balance") or 0
            application.additional_notes = form.cleaned_data.get("additional_notes") or ""

            created_user = None

            if not application.user:
                base_username = slugify(application.full_name) or "resident"
                username = f"{base_username}-{application.id}"

                counter = 1
                original_username = username

                while User.objects.filter(username=username).exists():
                    counter += 1
                    username = f"{original_username}-{counter}"

                created_user = User.objects.create_user(
                    username=username,
                    email=application.email,
                    password=None,
                    role="tenant",
                    is_staff=False,
                    is_superuser=False,
                )
                created_user.refresh_invite_code()

                application.user = created_user

            application.save()
            if application.user and not application.user.has_usable_password():
                application.user.refresh_invite_code()
            ensure_onboarding_documents(application)

            email_sent = False
            email_error = ""

            try:
                email_sent = send_resident_invite_email(application)
            except Exception as exc:
                email_error = str(exc)

            if email_sent:
                messages.success(
                    request,
                    "Application approved and resident onboarding invite email sent.",
                )
            else:
                messages.warning(
                    request,
                    "Application approved, but the invite email was not sent. Use the backup invite code below.",
                )

            return render(request, "landlord_create_tenant_success.html", {
                "application": application,
                "created_user": application.user,
                "email_sent": email_sent,
                "email_error": email_error,
            })

    else:
        form = LandlordCreateTenantForm(initial={
            "monthly_rent": application.monthly_rent,
            "balance": application.balance,
            "deposit_required": application.deposit_required,
            "deposit_paid": application.deposit_paid,
            "deposit_payment_plan": application.deposit_payment_plan,
            "utility_monthly": application.utility_monthly,
            "utility_balance": application.utility_balance,
            "space_type": application.space_type,
            "space_label": application.space_label,
        })

    return render(request, "landlord_create_tenant.html", {
        "form": form,
        "application": application,
    })
