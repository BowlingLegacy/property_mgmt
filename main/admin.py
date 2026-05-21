from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    User,
    Property,
    PropertyImage,
    HousingApplication,
    ApplicantDocument,
    BlogPost,
    BlogComment,
    RentHistory,
    Payment,
    FinancialUpload,
    FinancialEntry,
    ResidentMessage,
    SignedDocument,
    PropertyOwnerIntake,
    LandlordIntake,
    ExistingResidentIntake,
)
from django.utils import timezone

from .invite_utils import create_pending_portal_user, send_portal_access_invite_email


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        ("Login", {
            "fields": (
                "username",
                "password",
                "email",
                "role",
                "invite_code",
                "invite_code_created_at",
                "invite_code_used_at",
                "is_active",
            )
        }),
        ("Resident Link", {
            "fields": (
                "linked_resident_profile",
                "resident_property",
                "resident_unit",
                "resident_monthly_rent",
                "resident_balance",
            )
        }),
        ("Important Dates", {
            "fields": (
                "last_login",
                "date_joined",
            )
        }),
    )

    add_fieldsets = (
        ("Create Login Account", {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "role",
                "password1",
                "password2",
            ),
        }),
    )

    readonly_fields = (
        "invite_code",
        "invite_code_created_at",
        "invite_code_used_at",
        "linked_resident_profile",
        "resident_property",
        "resident_unit",
        "resident_monthly_rent",
        "resident_balance",
        "last_login",
        "date_joined",
    )

    list_display = (
        "username",
        "email",
        "role",
        "invite_code",
        "resident_unit",
        "resident_balance",
        "is_active",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "invite_code",
    )

    ordering = ("username",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.exclude(is_superuser=True)

    def get_resident_profile(self, obj):
        if not obj:
            return None
        return getattr(obj, "resident_profile", None)

    def linked_resident_profile(self, obj):
        profile = self.get_resident_profile(obj)
        return profile.full_name if profile else "No resident file linked"

    def resident_property(self, obj):
        profile = self.get_resident_profile(obj)
        if profile and profile.property:
            return profile.property.name
        return "—"

    def resident_unit(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile:
            return "—"
        return f"{profile.space_type} {profile.space_label}".strip() or "—"

    def resident_monthly_rent(self, obj):
        profile = self.get_resident_profile(obj)
        return f"${profile.monthly_rent}" if profile else "—"

    def resident_balance(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile:
            return "—"
        return "No balance due" if profile.balance <= 0 else f"${profile.balance}"

    def save_model(self, request, obj, form, change):
        if obj.role in ["tenant", "property_owner"]:
            obj.is_staff = False
            obj.is_superuser = False

        elif obj.role in ["landlord", "assistant", "admin"]:
            obj.is_staff = True
            if obj.role != "admin":
                obj.is_superuser = False

        super().save_model(request, obj, form, change)


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
    list_display = ("name", "availability_status", "available_date", "owner_email")


@admin.register(PropertyOwnerIntake)
class PropertyOwnerIntakeAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "company_name",
        "email",
        "status",
        "portal_invite_code",
        "property_count",
        "total_units",
        "needs_accounting",
        "needs_data_migration",
        "created_at",
    )
    list_filter = (
        "needs_accounting",
        "needs_data_migration",
        "needs_rent_collection",
        "needs_screening",
        "created_at",
    )
    search_fields = (
        "full_name",
        "company_name",
        "email",
        "phone",
        "current_software",
    )
    readonly_fields = ("portal_invite_code", "invite_sent_at", "created_at")
    actions = ("send_property_owner_portal_invites",)

    def portal_invite_code(self, obj):
        if obj.user and obj.user.invite_code:
            return obj.user.invite_code
        if obj.status == "registered":
            return "Account created"
        return "Not issued"

    @admin.action(description="Approve selected owner intakes and send portal invite")
    def send_property_owner_portal_invites(self, request, queryset):
        self.send_portal_invites(request, queryset, "property_owner", "Property Owner")

    def send_portal_invites(self, request, queryset, role, role_label):
        sent = 0
        codes = []

        for intake in queryset:
            user = intake.user

            if user and user.has_usable_password():
                continue

            if not user:
                user = create_pending_portal_user(intake.full_name, intake.email, role, intake.id)
                intake.user = user

            user.refresh_invite_code()
            intake.status = "invited"
            intake.invite_sent_at = timezone.now()
            intake.save(update_fields=["user", "status", "invite_sent_at"])
            codes.append(f"{intake.email}: {user.invite_code}")

            try:
                if send_portal_access_invite_email(user, intake.full_name, role_label):
                    sent += 1
            except Exception as exc:
                self.message_user(request, f"Invite email failed for {intake.email}: {exc}", level="warning")

        if codes:
            self.message_user(request, f"Invite codes issued: {' | '.join(codes)}")

        self.message_user(request, f"{sent} {role_label.lower()} invite email(s) sent.")


@admin.register(LandlordIntake)
class LandlordIntakeAdmin(PropertyOwnerIntakeAdmin):
    list_display = (
        "full_name",
        "email",
        "phone",
        "address",
        "status",
        "portal_invite_code",
        "created_at",
    )
    list_filter = (
        "status",
        "created_at",
    )
    search_fields = ("full_name", "email", "phone", "address")
    fields = (
        "email",
        "full_name",
        "phone",
        "address",
        "status",
        "portal_invite_code",
        "invite_sent_at",
        "created_at",
    )
    actions = ("send_landlord_portal_invites",)

    @admin.action(description="Send selected landlord portal invite")
    def send_landlord_portal_invites(self, request, queryset):
        self.send_portal_invites(request, queryset, "landlord", "Landlord")


@admin.register(ExistingResidentIntake)
class ExistingResidentIntakeAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "property",
        "email",
        "phone",
        "has_valid_odl",
        "years_at_residence",
        "move_in_month",
        "created_at",
    )
    list_filter = ("property", "has_valid_odl", "created_at")
    search_fields = ("first_name", "middle_name", "last_name", "email", "phone", "property__name")
    readonly_fields = ("created_at",)


class ApplicantDocumentInline(admin.TabularInline):
    model = ApplicantDocument
    extra = 0
    can_delete = False

    fields = (
        "name",
        "document_type",
        "file",
        "status",
        "needs_signature",
        "signed_at",
        "locked",
    )

    readonly_fields = (
        "signed_at",
        "submitted_at",
        "locked",
        "created_at",
    )


class ResidentMessageInline(admin.TabularInline):
    model = ResidentMessage
    extra = 0
    can_delete = False

    fields = (
        "message_type",
        "subject",
        "message",
        "status",
        "locked",
        "created_at",
    )

    readonly_fields = (
        "message_type",
        "subject",
        "message",
        "locked",
        "created_at",
    )


class SignedDocumentInline(admin.TabularInline):
    model = SignedDocument
    extra = 0
    can_delete = False

    readonly_fields = (
        "document_type",
        "title",
        "resident_signature",
        "signed_at",
        "locked",
        "created_at",
    )

    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False

    readonly_fields = (
        "payment_type",
        "payment_method",
        "description",
        "reference_number",
        "amount",
        "status",
        "recorded_by",
        "received_at",
        "created_at",
    )

    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


class RentHistoryInline(admin.TabularInline):
    model = RentHistory
    extra = 0
    can_delete = False

    readonly_fields = (
        "rent_amount",
        "effective_date",
        "created_at",
    )

    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(HousingApplication)
class HousingApplicationAdmin(admin.ModelAdmin):
    inlines = [
        ApplicantDocumentInline,
        SignedDocumentInline,
        ResidentMessageInline,
        PaymentInline,
        RentHistoryInline,
    ]

    list_display = (
        "full_name",
        "user",
        "property",
        "space_label",
        "monthly_rent",
        "balance",
        "utility_balance",
        "deposit_paid",
    )

    list_filter = (
        "property",
        "space_type",
    )

    search_fields = (
        "full_name",
        "phone",
        "email",
        "space_label",
        "user__username",
        "user__invite_code",
    )

    fieldsets = (
        ("Resident File Link", {
            "fields": (
                "user",
                "property",
                "space_type",
                "space_label",
            )
        }),
        ("Resident Information", {
            "fields": (
                "full_name",
                "phone",
                "email",
                "age",
            )
        }),
        ("Rent / Deposit / Utilities", {
            "fields": (
                "monthly_rent",
                "balance",
                "rent_due_day",
                "lease_start_date",
                "deposit_required",
                "deposit_paid",
                "utility_monthly",
                "utility_balance",
            )
        }),
        ("Address History", {
            "fields": (
                "current_address",
                "current_address_length",
                "previous_address_1",
                "previous_address_1_length",
                "previous_address_2",
                "previous_address_2_length",
                "previous_address_3",
                "previous_address_3_length",
            )
        }),
        ("Identification", {
            "fields": (
                "drivers_license_number",
                "has_valid_odl",
                "oregon_id_number",
                "id_upload",
            )
        }),
        ("Income", {
            "fields": (
                "income_source",
                "monthly_income",
                "employer_name",
                "employment_length",
            )
        }),
        ("Background / Recovery / Notes", {
            "fields": (
                "previous_evictions",
                "in_recovery",
                "drug_of_choice",
                "on_parole",
                "parole_officer_name",
                "parole_officer_phone",
                "felony_history",
                "odoc_time_served",
                "housing_need",
                "additional_notes",
            )
        }),
        ("References", {
            "fields": (
                "reference_1_name",
                "reference_1_phone",
                "reference_1_relationship",
                "reference_1_type",
                "reference_2_name",
                "reference_2_phone",
                "reference_2_relationship",
                "reference_2_type",
            )
        }),
        ("Acknowledgments", {
            "fields": (
                "sobriety_acknowledgment",
                "unconditional_regard_acknowledgment",
                "created_at",
            )
        }),
    )

    readonly_fields = ("created_at",)


@admin.register(ResidentMessage)
class ResidentMessageAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "application",
        "resident_property",
        "message_type",
        "subject",
        "status",
        "locked",
    )

    list_filter = (
        "status",
        "message_type",
        "application__property",
        "locked",
    )

    search_fields = (
        "subject",
        "message",
        "application__full_name",
        "application__email",
        "application__space_label",
    )

    readonly_fields = (
        "application",
        "message_type",
        "subject",
        "message",
        "locked",
        "created_at",
    )

    fields = (
        "application",
        "message_type",
        "subject",
        "message",
        "status",
        "locked",
        "created_at",
    )

    ordering = ("-created_at",)

    def resident_property(self, obj):
        if obj.application and obj.application.property:
            return obj.application.property.name
        return "No Property"


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "property", "author", "created_at")
    list_filter = ("property", "created_at")
    search_fields = ("title", "body", "property__name", "author__username")


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "approved", "created_at")
    list_filter = ("approved", "post__property")
    search_fields = ("name", "email", "comment", "post__title", "post__property__name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "payment_type",
        "payment_method",
        "amount",
        "status",
        "reference_number",
        "recorded_by",
        "created_at",
    )

    list_filter = (
        "payment_type",
        "payment_method",
        "status",
        "created_at",
    )

    readonly_fields = (
        "application",
        "payment_type",
        "payment_method",
        "description",
        "reference_number",
        "notes",
        "amount",
        "status",
        "recorded_by",
        "received_at",
        "stripe_session_id",
        "stripe_payment_intent",
        "created_at",
    )


@admin.register(RentHistory)
class RentHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "rent_amount", "effective_date")


class FinancialEntryInline(admin.TabularInline):
    model = FinancialEntry
    extra = 0
    can_delete = False

    readonly_fields = (
        "category",
        "description",
        "amount",
        "month",
        "year",
        "sheet_name",
        "row_number",
    )

    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(FinancialUpload)
class FinancialUploadAdmin(admin.ModelAdmin):
    inlines = [FinancialEntryInline]

    list_display = (
        "name",
        "uploaded_at",
        "parsed_at",
    )


@admin.register(FinancialEntry)
class FinancialEntryAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "description",
        "amount",
        "month",
        "year",
        "property_name",
        "sheet_name",
        "row_number",
    )

    list_filter = (
        "year",
        "month",
        "category",
    )

    search_fields = (
        "description",
        "category",
        "sheet_name",
    )

    ordering = (
        "year",
        "month",
        "category",
    )

    readonly_fields = (
        "upload",
        "property_name",
        "sheet_name",
        "row_number",
        "entry_date",
        "month",
        "year",
        "entry_type",
        "category",
        "description",
        "amount",
        "created_at",
    )

    def has_add_permission(self, request):
        return False
