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


# =========================
# USER ADMIN
# =========================
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
            return "No resident profile found"
        return profile.full_name

    def resident_property(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile or not profile.property:
            return "—"
        return profile.property.name

    def resident_unit(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile:
            return "—"

        parts = []
        if profile.space_type:
            parts.append(profile.space_type)
        if profile.space_label:
            parts.append(profile.space_label)

        return " ".join(parts) if parts else "—"

    def resident_monthly_rent(self, obj):
        profile = self.get_resident_profile(obj)
        return f"${profile.monthly_rent}" if profile else "—"

    def resident_balance(self, obj):
        profile = self.get_resident_profile(obj)
        if not profile:
            return "—"
        return "No balance due" if profile.balance <= 0 else f"${profile.balance}"


# =========================
# PROPERTY ADMIN
# =========================
class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
    list_display = ("name", "availability_status", "available_date", "owner_email")


# =========================
# APPLICATION ADMIN
# =========================
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
        "created_at",
    )

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

    def has_add_permission(self, request, obj=None):
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
        "space_label",
        "monthly_rent",
        "balance",
        "utility_balance",
        "deposit_paid",
    )


# =========================
# BLOG
# =========================
@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "approved", "created_at")
    list_filter = ("approved",)


# =========================
# PAYMENTS
# =========================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "payment_type",
        "amount",
        "status",
        "created_at",
    )

    readonly_fields = (
        "application",
        "payment_type",
        "amount",
        "status",
        "created_at",
    )


@admin.register(RentHistory)
class RentHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "rent_amount", "effective_date")


# =========================
# FINANCIALS
# =========================
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
