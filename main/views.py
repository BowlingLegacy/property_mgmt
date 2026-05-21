from collections import OrderedDict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import csv

import stripe

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Count, Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .forms import (
    InviteCodeForm,
    BlogCommentForm,
    HousingApplicationForm,
    FinancialUploadForm,
    SignUpForm,
    ManualPaymentForm,
    ResidentProfilePhotoForm,
    ReplacementInviteCodeForm,
    PropertyOwnerIntakeForm,
    LandlordSignUpForm,
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
    ApplicantDocument,
    SignedDocument,
    PropertyOwnerIntake,
    LandlordIntake,
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


def apply_completed_payment_to_balance(payment):
    application = payment.application

    if payment.payment_type == "rent":
        application.balance = max(Decimal("0.00"), application.balance - payment.amount)

    elif payment.payment_type == "deposit":
        application.deposit_paid = min(application.deposit_required, application.deposit_paid + payment.amount)

    elif payment.payment_type == "utility":
        application.utility_balance = max(Decimal("0.00"), application.utility_balance - payment.amount)

    elif payment.payment_type == "other" and "combined" in payment.description.lower():
        remaining = payment.amount

        rent_due = application.balance if application.balance > 0 else Decimal("0.00")
        rent_paid = min(rent_due, remaining)
        application.balance = max(Decimal("0.00"), application.balance - rent_paid)
        remaining -= rent_paid

        deposit_due = max(application.deposit_required - application.deposit_paid, Decimal("0.00"))
        deposit_paid = min(deposit_due, remaining)
        application.deposit_paid = min(application.deposit_required, application.deposit_paid + deposit_paid)
        remaining -= deposit_paid

        utility_due = application.utility_balance if application.utility_balance > 0 else Decimal("0.00")
        utility_paid = min(utility_due, remaining)
        application.utility_balance = max(Decimal("0.00"), application.utility_balance - utility_paid)

    application.save()


def home(request):
    properties = Property.objects.all()
    posts = BlogPost.objects.filter(property__isnull=True).order_by("-created_at")[:5]
    return render(request, "home.html", {"properties": properties, "posts": posts})
    
def properties_list(request):
    properties = Property.objects.all().order_by("name")

    return render(request, "properties.html", {
        "properties": properties,
    })

def creed(request):
    return render(request, "creed.html")


def who_we_serve(request):
    return render(request, "who_we_serve.html")


def property_owner_intake(request):
    form = PropertyOwnerIntakeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your property owner questionnaire has been submitted.")
        return redirect("property_owner_intake_success")

    return render(request, "property_owner_intake.html", {"form": form})


def property_owner_intake_success(request):
    return render(request, "property_owner_intake_success.html")


def apply(request):
    property_id = request.GET.get("property") or request.POST.get("property")
    property_obj = None

    if property_id:
        property_obj = get_object_or_404(Property, pk=property_id)

    if request.method == "POST":
        form = HousingApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            if property_obj:
                application.property = property_obj
            application.save()
            return redirect("apply_success")
    else:
        form = HousingApplicationForm()
    return render(request, "apply.html", {
        "form": form,
        "property": property_obj,
    })


def apply_success(request):
    return render(request, "apply_success.html")


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")


def signup(request):
    pending_user_id = request.session.get("pending_portal_user_id") or request.session.get("pending_resident_user_id")
    pending_profile_id = request.session.get("pending_resident_profile_id")

    if not pending_user_id:
        messages.error(request, "Please enter your invite code before creating an account.")
        return redirect("enter_invite_code")

    pending_user = get_object_or_404(User, id=pending_user_id)
    profile = None
    owner_intake = None
    landlord_intake_obj = None

    if pending_profile_id:
        profile = get_object_or_404(HousingApplication, id=pending_profile_id)
    elif pending_user.role == "property_owner":
        owner_intake = get_object_or_404(PropertyOwnerIntake, user=pending_user)
    elif pending_user.role == "landlord":
        landlord_intake_obj = get_object_or_404(LandlordIntake, user=pending_user)
    else:
        messages.error(request, "No portal intake is connected to this code yet.")
        return redirect("enter_invite_code")

    if not pending_user.invite_code_is_valid():
        request.session.pop("pending_portal_user_id", None)
        request.session.pop("pending_resident_user_id", None)
        request.session.pop("pending_resident_profile_id", None)
        messages.error(request, "That invite code expired. Request a new code to continue.")
        return redirect("request_invite_code")

    if request.method == "POST":
        form_class = LandlordSignUpForm if pending_user.role == "landlord" else SignUpForm
        form = form_class(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.role = pending_user.role
            user.email = form.cleaned_data.get("email") or pending_user.email
            user.is_staff = user.role in ["landlord", "assistant"]
            user.is_superuser = False
            user.save()

            if profile:
                profile.user = user
                profile.save()

            if owner_intake:
                owner_intake.user = user
                owner_intake.status = "registered"
                owner_intake.save(update_fields=["user", "status"])

            if landlord_intake_obj:
                landlord_intake_obj.full_name = form.cleaned_data.get("full_name", "")
                landlord_intake_obj.phone = form.cleaned_data.get("phone", "")
                landlord_intake_obj.address = form.cleaned_data.get("address", "")
                landlord_intake_obj.user = user
                landlord_intake_obj.status = "registered"
                landlord_intake_obj.save(update_fields=["full_name", "phone", "address", "user", "status"])

            if not pending_user.has_usable_password() and pending_user.id != user.id:
                pending_user.delete()
            else:
                pending_user.mark_invite_code_used()

            request.session.pop("pending_portal_user_id", None)
            request.session.pop("pending_resident_user_id", None)
            request.session.pop("pending_resident_profile_id", None)

            login(request, user)
            messages.success(request, "Your portal account is ready.")
            from .auth_views import dashboard_for_user
            return redirect(dashboard_for_user(user))
    else:
        form_class = LandlordSignUpForm if pending_user.role == "landlord" else SignUpForm
        initial = {"email": pending_user.email}

        if landlord_intake_obj:
            initial.update({
                "full_name": landlord_intake_obj.full_name,
                "phone": landlord_intake_obj.phone,
                "address": landlord_intake_obj.address,
            })

        form = form_class(initial=initial)

    return render(request, "signup.html", {
        "form": form,
        "application": profile,
        "pending_role": pending_user.get_role_display(),
    })


def enter_invite_code(request):
    form = InviteCodeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["invite_code"].upper()
        user_with_code = User.objects.filter(invite_code=code).first()

        if not user_with_code:
            messages.error(request, "Invalid access code.")
            return redirect("enter_invite_code")

        if not user_with_code.invite_code_is_valid():
            messages.error(request, "That invite code expired. Request a new code to continue.")
            return redirect("request_invite_code")

        profile = HousingApplication.objects.filter(user=user_with_code).first()
        if not profile and user_with_code.role == "tenant":
            profile = HousingApplication.objects.filter(email=user_with_code.email).first()

        owner_intake = PropertyOwnerIntake.objects.filter(user=user_with_code).first()
        landlord_intake_obj = LandlordIntake.objects.filter(user=user_with_code).first()

        if not profile and not owner_intake and not landlord_intake_obj:
            messages.error(request, "No approved portal intake is connected to this code yet.")
            return redirect("enter_invite_code")

        request.session["pending_portal_user_id"] = user_with_code.id
        request.session["pending_resident_user_id"] = user_with_code.id
        if profile:
            request.session["pending_resident_profile_id"] = profile.id
        else:
            request.session.pop("pending_resident_profile_id", None)

        messages.success(request, "Invite code accepted. Create your login to finish setup.")
        return redirect("signup")

    return render(request, "enter_invite_code.html", {"form": form})


def request_invite_code(request):
    form = ReplacementInviteCodeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        profile = (
            HousingApplication.objects
            .select_related("user")
            .filter(email__iexact=email, user__isnull=False)
            .first()
        )

        if profile and profile.user and not profile.user.has_usable_password():
            try:
                profile.user.refresh_invite_code()
                from .landlord_views import send_resident_invite_email
                send_resident_invite_email(profile)
            except Exception:
                pass
        else:
            portal_intake = (
                PropertyOwnerIntake.objects.select_related("user")
                .filter(email__iexact=email, user__isnull=False)
                .first()
            )
            role_label = "Property Owner"

            if not portal_intake:
                portal_intake = (
                    LandlordIntake.objects.select_related("user")
                    .filter(email__iexact=email, user__isnull=False)
                    .first()
                )
                role_label = "Landlord"

            if portal_intake and portal_intake.user and not portal_intake.user.has_usable_password():
                try:
                    portal_intake.user.refresh_invite_code()
                    from .invite_utils import send_portal_access_invite_email
                    send_portal_access_invite_email(portal_intake.user, portal_intake.full_name, role_label)
                except Exception:
                    pass

        messages.success(
            request,
            "If an approved unregistered portal intake matches that email, a new invite code has been sent.",
        )
        return redirect("enter_invite_code")

    return render(request, "request_invite_code.html", {"form": form})

def get_landlord_workspace_context():
    applications = (
        HousingApplication.objects
        .select_related("property", "user")
        .all()
        .order_by("property__name", "space_label", "full_name")
    )

    properties = Property.objects.all().order_by("name")
    payments = Payment.objects.all().order_by("-created_at")[:25]

    resident_messages = (
        ResidentMessage.objects
        .select_related("application", "application__property")
        .all()
        .order_by("application__property__name", "-created_at")
    )

    new_applications = (
        HousingApplication.objects
        .select_related("property", "user")
        .filter(user__isnull=True)
        .order_by("-created_at")
    )

    new_messages = (
        ResidentMessage.objects
        .select_related("application", "application__property")
        .filter(status="submitted")
        .order_by("-created_at")
    )

    new_documents = (
        ApplicantDocument.objects
        .select_related("application", "application__property")
        .filter(status="uploaded", landlord_notified=False)
        .order_by("-created_at")
    )

    landlord_inbox = OrderedDict()

    for resident_message in resident_messages:
        application = resident_message.application
        property_name = "No Property"

        if application and application.property:
            property_name = application.property.name

        landlord_inbox.setdefault(property_name, [])
        landlord_inbox[property_name].append(resident_message)

    new_message_count = new_messages.count()

    return {
        "applications": applications,
        "properties": properties,
        "payments": payments,
        "landlord_inbox": landlord_inbox,
        "new_message_count": new_message_count,
        "new_applications": new_applications,
        "new_application_count": new_applications.count(),
        "new_messages": new_messages,
        "new_documents": new_documents,
        "new_document_count": new_documents.count(),
        "attention_count": (
            new_applications.count()
            + new_message_count
            + new_documents.count()
        ),
    }


@login_required
@user_passes_test(staff_required)
def landlord_dashboard(request):
    return render(request, "landlord_dashboard.html", get_landlord_workspace_context())


@login_required
@user_passes_test(staff_required)
def landlord_attention(request):
    return render(request, "landlord_attention.html", get_landlord_workspace_context())


@login_required
@user_passes_test(staff_required)
def landlord_resident_files(request):
    return render(request, "landlord_resident_files.html", get_landlord_workspace_context())
def get_superadmin_workspace_context():
    properties = Property.objects.all().order_by("name")
    users = User.objects.all().order_by("username")
    applications = HousingApplication.objects.select_related("property", "user").all().order_by("property__name", "space_label", "full_name")
    completed_payments = Payment.objects.filter(status="completed")
    site_payment_total = completed_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    owner_buckets = OrderedDict()

    for property_obj in properties:
        owner_email = (property_obj.owner_email or "").strip()
        owner_label = owner_email or "Unassigned Owner"

        owner_buckets.setdefault(owner_label, [])
        owner_buckets[owner_label].append(property_obj)

    owner_groups = [
        {
            "email": owner_label,
            "property_count": len(owner_properties),
            "properties": owner_properties,
        }
        for owner_label, owner_properties in owner_buckets.items()
    ]
    
    recent_messages = (
        ResidentMessage.objects
        .select_related("application", "application__property")
        .all()
        .order_by("-created_at")[:10]
)
    
    context = {
        "properties": properties,
        "users": users,
        "applications": applications,
        "recent_messages": recent_messages,
        "owner_groups": owner_groups,
        "site_payment_total": site_payment_total,
    }

    return context


@login_required
@user_passes_test(staff_required)
def superadmin_dashboard(request):

    if not request.user.is_superuser and request.user.role != "admin":
        return redirect("tenant_dashboard")

    return render(
        request,
        "superadmin_dashboard.html",
        get_superadmin_workspace_context()
    )


@login_required
@user_passes_test(staff_required)
def superadmin_owners(request):
    if not request.user.is_superuser and request.user.role != "admin":
        return redirect("tenant_dashboard")

    return render(request, "superadmin_owners.html", get_superadmin_workspace_context())


@login_required
@user_passes_test(staff_required)
def superadmin_residents(request):
    if not request.user.is_superuser and request.user.role != "admin":
        return redirect("tenant_dashboard")

    return render(request, "superadmin_residents.html", get_superadmin_workspace_context())
@login_required
@user_passes_test(staff_required)
def landlord_message_detail(request, message_id):
    resident_message = get_object_or_404(
        ResidentMessage.objects.select_related("application", "application__property"),
        id=message_id,
    )

    if request.method == "POST":
        new_status = request.POST.get("status")

        if new_status in ["submitted", "reviewed", "closed"]:
            resident_message.status = new_status
            resident_message.save()
            messages.success(request, "Message status updated.")

        return redirect("landlord_message_detail", message_id=resident_message.id)

    return render(request, "landlord_message_detail.html", {
        "resident_message": resident_message,
        "application": resident_message.application,
    })


@login_required
@user_passes_test(staff_required)
def mark_document_reviewed(request, document_id):
    document = get_object_or_404(
        ApplicantDocument.objects.select_related("application"),
        id=document_id,
    )

    document.landlord_notified = True
    document.save(update_fields=["landlord_notified"])

    messages.success(request, f"{document.name} marked reviewed.")
    return redirect("landlord_dashboard")


@login_required
def tenant_dashboard(request):
    request.session.set_expiry(0)

    application = getattr(request.user, "resident_profile", None)
    is_superadmin_inspecting = False

    if (request.user.is_superuser or getattr(request.user, "role", "") == "admin") and request.GET.get("resident"):
        application = get_object_or_404(
            HousingApplication.objects.select_related("property", "user"),
            id=request.GET.get("resident"),
        )
        is_superadmin_inspecting = True

    payments = []
    resident_messages = []
    profile_photo_form = None
    total_due = Decimal("0.00")

    if application:
        payments = application.payments.all().order_by("-created_at")
        resident_messages = application.resident_messages.all().order_by("-created_at")
        if not is_superadmin_inspecting:
            profile_photo_form = ResidentProfilePhotoForm(instance=application)

        rent_due = application.balance if application.balance > 0 else Decimal("0.00")
        deposit_due = max(application.deposit_required - application.deposit_paid, Decimal("0.00"))
        utility_due = application.utility_balance if application.utility_balance > 0 else Decimal("0.00")

        total_due = rent_due + deposit_due + utility_due

    return render(request, "tenant_dashboard.html", {
        "application": application,
        "payments": payments,
        "resident_messages": resident_messages,
        "profile_photo_form": profile_photo_form,
        "is_superadmin_inspecting": is_superadmin_inspecting,
        "total_due": total_due,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    })


@login_required
def update_resident_profile_photo(request):
    if request.method != "POST":
        return redirect("tenant_dashboard")

    application = getattr(request.user, "resident_profile", None)

    if not application:
        messages.error(request, "No resident file connected.")
        return redirect("tenant_dashboard")

    form = ResidentProfilePhotoForm(request.POST, request.FILES, instance=application)

    if form.is_valid():
        form.save()
        messages.success(request, "Profile photo updated.")
    else:
        messages.error(request, "Please choose a valid image file.")

    return redirect("tenant_dashboard")


@login_required
def upload_resident_document(request):
    if request.method != "POST":
        return redirect("tenant_dashboard")

    application = getattr(request.user, "resident_profile", None)

    if not application:
        messages.error(request, "No resident file connected.")
        return redirect("tenant_dashboard")

    document_type = request.POST.get("document_type", "other")
    name = request.POST.get("name", "").strip()
    uploaded_file = request.FILES.get("file")

    if not name or not uploaded_file:
        messages.error(request, "Document name and file are required.")
        return redirect("tenant_dashboard")

    ApplicantDocument.objects.create(
        application=application,
        document_type=document_type,
        name=name,
        file=uploaded_file,
        status="uploaded",
        locked=False,
    )

    owner_email = "BowlingLegacyLLC@outlook.com"
    if application.property and application.property.owner_email:
        owner_email = application.property.owner_email

    send_mail(
        subject=f"New Resident Document Uploaded: {name}",
        message=f"""
A resident uploaded a new document.

Property: {application.property.name if application.property else "No Property"}
Resident: {application.full_name}
Room/Space: {application.space_type} {application.space_label}

Document:
{name}

Type:
{document_type}
""",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[owner_email],
        fail_silently=True,
    )

    messages.success(request, "Your document has been uploaded and filed.")
    return redirect("tenant_dashboard")


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

    owner_email = "BowlingLegacyLLC@outlook.com"
    if application.property and application.property.owner_email:
        owner_email = application.property.owner_email

    send_mail(
        subject=f"New Resident Request Filed: {subject}",
        message=f"""
A new resident request/message has been filed.

Property: {application.property.name if application.property else "No Property"}
Resident: {application.full_name}
Unit/Space: {application.space_type} {application.space_label}

Type: {message_type}

Subject:
{subject}

Message:
{message}
""",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[owner_email],
        fail_silently=True,
    )

    messages.success(request, "Your message/request has been submitted and filed.")
    return redirect("tenant_dashboard")


@login_required
@user_passes_test(staff_required)
def payment_log(request):
    completed_payments = (
        Payment.objects
        .filter(status="completed")
        .select_related("application", "application__property")
        .order_by("application__property__name", "-created_at", "application__space_label", "application__full_name")
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

    return render(request, "payment_log.html", {"payment_log": payment_log_data})


@login_required
@user_passes_test(staff_required)
def record_manual_payment(request):
    if request.method == "POST":
        form = ManualPaymentForm(request.POST)

        if form.is_valid():
            payment = form.save(commit=False)
            payment.status = "completed"
            payment.recorded_by = request.user

            if not payment.received_at:
                payment.received_at = timezone.now()

            if not payment.description:
                payment.description = f"Manual {payment.get_payment_method_display()} payment"

            payment.save()
            apply_completed_payment_to_balance(payment)

            messages.success(request, "Manual payment recorded and resident balance updated.")
            return redirect("payment_receipt", payment_id=payment.id)
    else:
        initial = {}
        application_id = request.GET.get("application")

        if application_id:
            initial["application"] = application_id

        form = ManualPaymentForm(initial=initial)

    return render(request, "record_manual_payment.html", {"form": form})


@login_required
@user_passes_test(staff_required)
def payment_receipt(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("application", "application__property", "recorded_by"),
        id=payment_id,
    )

    return render(request, "payment_receipt.html", {"payment": payment})


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

        rent_paid = completed_payments.filter(payment_type="rent").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        utility_paid = completed_payments.filter(payment_type="utility").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

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

    return render(request, "rent_roll.html", {"rows": rows})


@login_required
@user_passes_test(staff_required)
def export_payment_log_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="payment_log.csv"'

    writer = csv.writer(response)
    writer.writerow(["Resident", "Property", "Payment Type", "Amount", "Status", "Date"])

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

    return response


@login_required
@user_passes_test(staff_required)
def export_rent_roll_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="rent_roll.csv"'

    writer = csv.writer(response)
    writer.writerow(["Resident", "Property", "Room", "Monthly Rent", "Balance", "Deposit Required", "Deposit Paid", "Utility Balance"])

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
    response["Content-Disposition"] = 'attachment; filename="t12_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Month", "Income", "Expenses", "Debt Service", "Cash Flow"])

    current_year = timezone.localdate().year

    for month in range(1, 13):
        income = Payment.objects.filter(status="completed", created_at__year=current_year, created_at__month=month).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        expenses = FinancialEntry.objects.filter(year=current_year, month=month, entry_type="operating_expense").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        debt_service = FinancialEntry.objects.filter(year=current_year, month=month, entry_type="debt_service").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        cash_flow = income - expenses - debt_service

        writer.writerow([date(current_year, month, 1).strftime("%B"), income, expenses, debt_service, cash_flow])

    return response


@login_required
@user_passes_test(staff_required)
def t12_report(request):
    year = timezone.localdate().year
    financial_entries = FinancialEntry.objects.filter(year=year)
    months = []

    for month_number in range(1, 13):
        online_income = Payment.objects.filter(status="completed", created_at__year=year, created_at__month=month_number).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        spreadsheet_income = financial_entries.filter(month=month_number, entry_type="income").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        operating_expenses = financial_entries.filter(month=month_number, entry_type="operating_expense").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        debt_service = financial_entries.filter(month=month_number, entry_type="debt_service").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        capital_expenses = financial_entries.filter(month=month_number, entry_type="capital_expense").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

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

    return render(request, "t12_report.html", {"year": year, "months": months})


@login_required
@user_passes_test(staff_required)
def financial_upload(request):
    if request.method == "POST":
        form = FinancialUploadForm(request.POST, request.FILES)

        if form.is_valid():
            upload = form.save()
            return redirect("parse_financial_upload", upload_id=upload.id)
    else:
        form = FinancialUploadForm()

    uploads = FinancialUpload.objects.all().order_by("-uploaded_at")
    return render(request, "financial_upload.html", {"form": form, "uploads": uploads})


@login_required
@user_passes_test(staff_required)
def parse_financial_upload(request, upload_id):
    upload = get_object_or_404(FinancialUpload, id=upload_id)
    upload.parsed_at = timezone.now()
    upload.save()

    return render(request, "financial_upload_parsed.html", {"upload": upload, "created": 0})


@login_required
@user_passes_test(staff_required)
def property_financials(request, property_name):
    property_obj = get_object_or_404(Property, name=property_name)
    residents = HousingApplication.objects.filter(property=property_obj)

    monthly_rent = sum([r.monthly_rent for r in residents], Decimal("0.00"))
    balances_due = sum([r.balance for r in residents], Decimal("0.00"))
    utilities_due = sum([r.utility_balance for r in residents], Decimal("0.00"))
    deposits_held = sum([r.deposit_paid for r in residents], Decimal("0.00"))

    completed_payments = Payment.objects.filter(application__property=property_obj, status="completed")
    total_collected = completed_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return render(request, "property_financials.html", {
        "property": property_obj,
        "residents": residents,
        "monthly_rent": monthly_rent,
        "balances_due": balances_due,
        "utilities_due": utilities_due,
        "deposits_held": deposits_held,
        "total_collected": total_collected,
    })


def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    gallery_images = property_obj.images.all()
    can_view_property_blog = user_can_view_property_blog(request.user, property_obj)
    posts = BlogPost.objects.none()

    if can_view_property_blog:
        posts = property_obj.blog_posts.prefetch_related("comments").select_related("author").order_by("-created_at")

    return render(request, "property_detail.html", {
        "property": property_obj,
        "gallery_images": gallery_images,
        "posts": posts,
        "can_view_property_blog": can_view_property_blog,
    })


def blog_detail(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    return render(request, "blog_detail.html", {"post": post})


def user_can_view_property_blog(user, property_obj):
    if not user.is_authenticated:
        return False

    if staff_required(user) or getattr(user, "role", "") == "admin":
        return True

    if property_obj.owner_email and user.email and property_obj.owner_email.lower() == user.email.lower():
        return True

    application = getattr(user, "resident_profile", None)
    return bool(application and application.property_id == property_obj.id)


def add_blog_comment(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)

    if post.property and not user_can_view_property_blog(request.user, post.property):
        return redirect(f"{reverse('login')}?next={reverse('property_detail', args=[post.property.id])}")

    if request.method == "POST":
        form = BlogCommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.approved = False
            comment.save()

    if post.property:
        return redirect("property_detail", pk=post.property.id)

    return redirect("home")


def printable_application(request, pk):
    application = get_object_or_404(HousingApplication, pk=pk)
    return render(request, "printable_application.html", {"application": application})


def get_resident_signed_document(request, document_id):
    application = getattr(request.user, "resident_profile", None)

    if not application:
        messages.error(request, "No resident file connected.")
        return None

    return get_object_or_404(
        SignedDocument,
        id=document_id,
        application=application,
    )


@login_required
def lease_sign(request):

    application = getattr(request.user, "resident_profile", None)

    if not application:
        messages.error(request, "No resident file connected.")
        return redirect("tenant_dashboard")

    signed_document = SignedDocument.objects.filter(
        application=application,
        document_type="lease",
    ).first()

    if not signed_document:
        signed_document = SignedDocument.objects.create(
            application=application,
            document_type="lease",
            title="Resident Lease Agreement",
            lease_sent_date=timezone.localdate(),
        )

    return render(request, "lease_sign.html", {
        "application": application,
        "signed_document": signed_document,
    })


@login_required
def onboarding_document(request, document_id):
    signed_document = get_resident_signed_document(request, document_id)

    if not signed_document:
        return redirect("tenant_dashboard")

    template_name = "lease_sign.html"

    if signed_document.document_type != "lease":
        template_name = "onboarding_document_sign.html"

    return render(request, template_name, {
        "application": signed_document.application,
        "signed_document": signed_document,
    })


@login_required
def submit_lease_signature(request):

    if request.method != "POST":
        return redirect("tenant_dashboard")

    application = getattr(request.user, "resident_profile", None)

    if not application:
        messages.error(request, "No resident file connected.")
        return redirect("tenant_dashboard")

    signed_document = SignedDocument.objects.filter(
        application=application,
        document_type="lease",
    ).first()

    if not signed_document:
        messages.error(request, "Lease document not found.")
        return redirect("tenant_dashboard")

    if signed_document.locked:
        messages.info(request, "This lease has already been signed.")
        return redirect("tenant_dashboard")

    signed_document.rent_initials = request.POST.get("rent_initials", "").strip()
    signed_document.sobriety_initials = request.POST.get("sobriety_initials", "").strip()
    signed_document.testing_initials = request.POST.get("testing_initials", "").strip()
    signed_document.guest_policy_initials = request.POST.get("guest_policy_initials", "").strip()
    signed_document.cleanliness_initials = request.POST.get("cleanliness_initials", "").strip()
    signed_document.disclosure_initials = request.POST.get("disclosure_initials", "").strip()

    signed_document.resident_signature = request.POST.get("resident_signature", "").strip()

    signed_document.signature_agreement = bool(
        request.POST.get("signature_agreement")
    )

    if not signed_document.resident_signature:
        messages.error(request, "Signature is required.")
        return redirect("lease_sign")

    if not signed_document.signature_agreement:
        messages.error(request, "You must agree to electronically sign.")
        return redirect("lease_sign")

    signed_document.signed_at = timezone.now()
    signed_document.locked = True

    signed_document.save()

    messages.success(
        request,
        "Lease agreement successfully signed and filed."
    )

    return redirect("tenant_dashboard")


@login_required
def submit_onboarding_document(request, document_id):
    if request.method != "POST":
        return redirect("tenant_dashboard")

    signed_document = get_resident_signed_document(request, document_id)

    if not signed_document:
        return redirect("tenant_dashboard")

    if signed_document.locked:
        messages.info(request, "This document has already been signed and filed.")
        return redirect("tenant_dashboard")

    if signed_document.document_type == "lease":
        return submit_lease_signature(request)

    signed_document.emergency_contact_name = request.POST.get("emergency_contact_name", "").strip()
    signed_document.emergency_contact_phone = request.POST.get("emergency_contact_phone", "").strip()
    signed_document.emergency_contact_relationship = request.POST.get("emergency_contact_relationship", "").strip()
    signed_document.emergency_medical_notes = request.POST.get("emergency_medical_notes", "").strip()
    signed_document.resident_signature = request.POST.get("resident_signature", "").strip()
    signed_document.signature_agreement = bool(request.POST.get("signature_agreement"))

    if signed_document.document_type == "emergency_contact":
        if not signed_document.emergency_contact_name or not signed_document.emergency_contact_phone:
            messages.error(request, "Emergency contact name and phone are required.")
            return redirect("onboarding_document", document_id=signed_document.id)

    if not signed_document.resident_signature:
        messages.error(request, "Signature is required.")
        return redirect("onboarding_document", document_id=signed_document.id)

    if not signed_document.signature_agreement:
        messages.error(request, "You must agree to electronically sign.")
        return redirect("onboarding_document", document_id=signed_document.id)

    signed_document.signed_at = timezone.now()
    signed_document.locked = True
    signed_document.save()

    messages.success(request, "Document signed and filed.")
    return redirect("tenant_dashboard")


@login_required 
def create_checkout_session(request, application_id, payment_type="rent"):
    application = get_object_or_404(HousingApplication, id=application_id)

    if not staff_required(request.user):
        user_application = getattr(request.user, "resident_profile", None)
        if not user_application or user_application.id != application.id:
            return JsonResponse({"error": "You are not authorized to pay this account."}, status=403)

    stale_before = timezone.now() - timedelta(minutes=30)
    Payment.objects.filter(
        application=application,
        payment_type=payment_type,
        status="pending",
        created_at__lt=stale_before,
    ).update(status="failed")

    existing_pending = Payment.objects.filter(
        application=application,
        payment_type=payment_type,
        status="pending",
    ).exists()

    if existing_pending:
        return JsonResponse({
            "error": "A payment is already pending. Please wait before trying again."
        })

    if payment_type == "rent" and application.balance <= 0:
        return JsonResponse({
            "error": "No rent balance due."
        })

    amount = Decimal("0.00")
    description = ""

    if payment_type == "rent":
        amount = application.balance if application.balance > 0 else application.monthly_rent
        description = "Rent Payment"

    elif payment_type == "deposit":
        amount = max(application.deposit_required - application.deposit_paid, Decimal("0.00"))
        description = "Deposit Payment"

    elif payment_type == "utility":
        amount = application.utility_balance if application.utility_balance > 0 else application.utility_monthly
        description = "Utility Payment"

    elif payment_type == "total":
        rent_due = application.balance if application.balance > 0 else Decimal("0.00")
        deposit_due = max(application.deposit_required - application.deposit_paid, Decimal("0.00"))
        utility_due = application.utility_balance if application.utility_balance > 0 else Decimal("0.00")

        amount = rent_due + deposit_due + utility_due
        description = "Combined Payment - Total Due"
        payment_type = "other"

    else:
        return JsonResponse({"error": "Invalid payment type"})

    if amount <= 0:
        return JsonResponse({"error": "No balance due"})

    payment = Payment.objects.create(
        application=application,
        payment_type=payment_type,
        payment_method="stripe_card",
        description=description,
        amount=amount,
        status="pending",
    )

    session = stripe.checkout.Session.create(
        payment_method_types=["card", "cashapp"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": description},
                "unit_amount": int(amount * 100),
            },
            "quantity": 1,
        }],
        success_url=request.build_absolute_uri("/payment-success/"),
        cancel_url=request.build_absolute_uri("/tenant-dashboard/"),
        metadata={"payment_id": str(payment.id)},
    )

    payment.stripe_session_id = session.id
    payment.save()

    return redirect(session.url)


def payment_success(request):
    return render(request, "payment_success.html")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        return HttpResponse(status=400)

    if event["type"] != "checkout.session.completed":
        return HttpResponse(status=200)

    session = event["data"]["object"]
    payment_id = session["metadata"]["payment_id"]

    if not payment_id:
        return HttpResponse(status=200)

    payment = Payment.objects.filter(id=payment_id).first()

    if not payment or payment.status == "completed":
        return HttpResponse(status=200)

    payment.status = "completed"
    payment.stripe_payment_intent = session["payment_intent"]
    payment.save()

    payment_method_types = session.get("payment_method_types", [])
    if "cashapp" in payment_method_types:
        payment.payment_method = "stripe_cashapp"
        payment.save()

    apply_completed_payment_to_balance(payment)

    application = payment.application
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
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[owner_email],
        fail_silently=True,
    )

    return HttpResponse(status=200)
