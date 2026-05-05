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
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("RentLogic Profile", {
            "fields": ("role", "invite_code"),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("RentLogic Profile", {
            "fields": ("email", "role", "invite_code"),
        }),
    )

    list_display = ("username", "email", "role", "is_staff", "is_active")
    search_fields = ("username", "email")


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
    list_display = ("name", "availability_status", "available_date")


class ApplicantDocumentInline(admin.TabularInline):
    model = ApplicantDocument
    extra = 0
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = (
        "amount",
        "status",
        "stripe_session_id",
        "stripe_payment_intent",
        "created_at",
    )
    can_delete = False


class RentHistoryInline(admin.TabularInline):
    model = RentHistory
    extra = 0


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
        "email",
        "phone",
        "monthly_rent",
        "balance",
        "rent_due_day",
        "created_at",
    )

    search_fields = (
        "full_name",
        "email",
        "phone",
    )

    list_filter = (
        "property",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )

    fieldsets = (
        ("Resident Profile", {
            "fields": (
                "property",
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
    list_display = ("application", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("application__full_name", "application__email", "stripe_session_id")


@admin.register(RentHistory)
class RentHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "rent_amount", "effective_date", "created_at")
    search_fields = ("application__full_name", "application__email")
