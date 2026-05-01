from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Property, PropertyImage, HousingApplication, ApplicantDocument, BlogPost


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


class ApplicantDocumentInline(admin.TabularInline):
    model = ApplicantDocument
    extra = 0
    can_delete = False

    fields = (
        "name",
        "document_type",
        "file_link",
        "status",
        "locked",
        "signed_at",
        "submitted_at",
        "created_at",
    )

    readonly_fields = (
        "name",
        "document_type",
        "file_link",
        "status",
        "locked",
        "signed_at",
        "submitted_at",
        "created_at",
    )

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View / Download</a>', obj.file.url)
        return "No file"

    file_link.short_description = "File"


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
    list_display = ("name", "address", "availability_status")
    list_filter = ("availability_status",)


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("property", "caption")


@admin.register(HousingApplication)
class HousingApplicationAdmin(admin.ModelAdmin):
    inlines = [ApplicantDocumentInline]

    list_display = (
        "full_name",
        "email",
        "phone",
        "property",
        "created_at",
        "print_application_link",
    )

    search_fields = ("full_name", "email", "phone")
    list_filter = ("property", "created_at")

    readonly_fields = (
        "property",
        "full_name",
        "phone",
        "email",
        "age",
        "current_address",
        "current_address_length",
        "previous_address_1",
        "previous_address_1_length",
        "previous_address_2",
        "previous_address_2_length",
        "previous_address_3",
        "previous_address_3_length",
        "drivers_license_number",
        "has_valid_odl",
        "oregon_id_number",
        "id_upload",
        "income_source",
        "monthly_income",
        "employer_name",
        "employment_length",
        "previous_evictions",
        "in_recovery",
        "drug_of_choice",
        "on_parole",
        "parole_officer_name",
        "parole_officer_phone",
        "felony_history",
        "odoc_time_served",
        "reference_1_name",
        "reference_1_phone",
        "reference_1_relationship",
        "reference_1_type",
        "reference_2_name",
        "reference_2_phone",
        "reference_2_relationship",
        "reference_2_type",
        "housing_need",
        "additional_notes",
        "sobriety_acknowledgment",
        "unconditional_regard_acknowledgment",
        "created_at",
        "print_application_link",
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def print_application_link(self, obj):
        if obj.pk:
            url = reverse("printable_application", args=[obj.pk])
            return format_html('<a href="{}" target="_blank">View / Print Application PDF Page</a>', url)
        return "Save application first"

    print_application_link.short_description = "Printable Application"


@admin.register(ApplicantDocument)
class ApplicantDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "application", "document_type", "status", "locked", "created_at")
    list_filter = ("document_type", "status", "locked", "created_at")
    search_fields = ("name", "application__full_name")

    readonly_fields = (
        "application",
        "name",
        "document_type",
        "file",
        "status",
        "needs_signature",
        "needs_initials",
        "signed_at",
        "submitted_at",
        "locked",
        "created_at",
    )

    exclude = ("landlord_notified",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "created_at")
    list_filter = ("published",)
