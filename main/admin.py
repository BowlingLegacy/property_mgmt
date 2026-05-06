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
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("RentLogic Resident File", {
            "fields": (
                "role",
                "invite_code",
                "linked_resident_profile",
                "resident_property",
                "resident_unit",
                "resident_monthly_rent",
                "resident_balance",
            ),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("RentLogic Profile", {
            "fields": ("email", "role", "invite_code"),
        }),
    )

    readonly_fields = (
        "linked_resident_profile",
        "resident_property",
        "resident_unit",
        "resident_monthly_rent",
        "resident_balance",
    )

    list_display = (
        "username",
        "email",
        "role",
        "resident_unit",
        "resident_balance",
        "is_staff",
        "is_active",
    )

    search_fields = ("username", "email")

    def get_resident_profile(self, obj):
        if not obj or not obj.email:
            return None
        return HousingApplication.objects.filter(email=obj.email).first()

    def linked_resident_profile(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile:
            return "No resident profile found by email match."
        return profile.full_name

    linked_resident_profile.short_description = "Linked Resident Profile"

    def resident_property(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile or not profile.property:
            return "—"
        return profile.property.name

    resident_property.short_description = "Property"

    def resident_unit(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile:
            return "—"

        unit_parts = []
        if profile.space_type:
            unit_parts.append(profile.space_type)
        if profile.space_label:
            unit_parts.append(profile.space_label)

        return " ".join(unit_parts) if unit_parts else "—"

    resident_unit.short_description = "Room / Unit"

    def resident_monthly_rent(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile:
            return "—"
        return f"${profile.monthly_rent}"

    resident_monthly_rent.short_description = "Monthly Rent"

    def resident_balance(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile:
            return "—"

        if profile.balance <= 0:
            return "No balance due"

        return f"${profile.balance}"

    resident_balance.short_description = "Current Balance"


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
    list_display = ("name", "availability_status", "available_date", "owner_email")
    search_fields = ("name", "address", "owner_email")


class ApplicantDocumentInline(admin.TabularInline):
    model = ApplicantDocument
    extra = 0
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False

    readonly_fields = (
        "payment_type",
        "description",
        "amount",
        "status",
        "stripe_session_id",
        "stripe_payment_intent",
        "created_at",
    )

    fields = (
        "payment_type",
        "description",
        "amount",
        "status",
        "stripe_session_id",
        "stripe_payment_intent",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
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

    fields = (
        "rent_amount",
        "effective_date",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HousingApplication)
class HousingApplicationAdmin(admin.ModelAdmin):
    inlines = [
        ApplicantDocumentInline,
        PaymentInline,
        RentHistoryInline,
    ]

    list_display = (
        "full_name",
        "property",
        "space_type",
        "space_label",
        "email",
        "phone",
        "monthly_rent",
        "balance",
        "utility_monthly",
        "utility_balance",
        "deposit_required",
        "deposit_paid",
        "rent_due_day",
        "created_at",
    )

    search_fields = (
        "full_name",
        "email",
        "phone",
        "space_type",
        "space_label",
    )

    list_filter = (
        "property",
        "space_type",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )

    fieldsets = (
        ("Resident Profile", {
            "fields": (
                "property",
                "space_type",
                "space_label",
                "full_name",
                "phone",
                "email",
                "age",
            )
        }),

        ("Rent Setup", {
            "fields": (
                "monthly_rent",
                "balance",
                "rent_due_day",
            )
        }),

        ("Deposit Setup", {
            "fields": (
                "deposit_required",
                "deposit_paid",
            )
        }),

        ("Utilities Setup", {
            "fields": (
                "utility_monthly",
                "utility_balance",
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

        ("Income / Employment", {
            "fields": (
                "income_source",
                "monthly_income",
                "employer_name",
                "employment_length",
            )
        }),

        ("Housing / Recovery / Background", {
            "fields": (
                "housing_need",
                "previous_evictions",
                "in_recovery",
                "drug_of_choice",
                "on_parole",
                "parole_officer_name",
                "parole_officer_phone",
                "felony_history",
                "odoc_time_served",
            )
        }),

        ("Current Address", {
            "classes": ("collapse",),
            "fields": (
                "current_address",
                "current_address_length",
            )
        }),

        ("Previous Addresses", {
            "classes": ("collapse",),
            "fields": (
                "previous_address_1",
                "previous_address_1_length",
                "previous_address_2",
                "previous_address_2_length",
                "previous_address_3",
                "previous_address_3_length",
            )
        }),

        ("References", {
            "classes": ("collapse",),
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
            )
        }),

        ("Notes / System", {
            "fields": (
                "additional_notes",
                "created_at",
            )
        }),
    )


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")
    ordering = ("-created_at",)


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "approved", "created_at")
    list_filter = ("approved", "created_at")
    search_fields = ("name", "email", "comment")
    actions = ["approve_comments"]

    def approve_comments(self, request, queryset):
        queryset.update(approved=True)

    approve_comments.short_description = "Approve selected comments"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "payment_type",
        "description",
        "amount",
        "status",
        "created_at",
    )

    list_filter = (
        "payment_type",
        "status",
        "created_at",
    )

    search_fields = (
        "application__full_name",
        "application__email",
        "stripe_session_id",
        "description",
    )

    readonly_fields = (
        "application",
        "payment_type",
        "description",
        "amount",
        "status",
        "stripe_session_id",
        "stripe_payment_intent",
        "created_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(RentHistory)
class RentHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "rent_amount", "effective_date", "created_at")
    search_fields = ("application__full_name", "application__email")

    readonly_fields = (
        "application",
        "rent_amount",
        "effective_date",
        "created_at",
    )

    def has_add_permission(self, request):
        return False


class FinancialEntryInline(admin.TabularInline):
    model = FinancialEntry
    extra = 0
    can_delete = False

    readonly_fields = (
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

    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FinancialUpload)
class FinancialUploadAdmin(admin.ModelAdmin):
    inlines = [FinancialEntryInline]

    list_display = (
        "name",
        "uploaded_at",
        "parsed_at",
        "entry_count",
    )

    readonly_fields = (
        "uploaded_at",
        "parsed_at",
    )

    search_fields = (
        "name",
        "notes",
    )

    def entry_count(self, obj):
        return obj.entries.count()

    entry_count.short_description = "Entries"


@admin.register(FinancialEntry)
class FinancialEntryAdmin(admin.ModelAdmin):
    list_display = (
        "property_name",
        "entry_type",
        "category",
        "amount",
        "month",
        "year",
        "sheet_name",
    )

    list_filter = (
        "entry_type",
        "year",
        "month",
        "sheet_name",
    )

    search_fields = (
        "property_name",
        "category",
        "description",
        "sheet_name",
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
