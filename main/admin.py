from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Property,
    PropertyImage,
    HousingApplication,
    ApplicantDocument,
    BlogPost,
    BlogComment,
)


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

    fields = (
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

    readonly_fields = (
        "locked",
        "created_at",
    )


@admin.register(HousingApplication)
class HousingApplicationAdmin(admin.ModelAdmin):
    inlines = [ApplicantDocumentInline]

    list_display = (
        "full_name",
        "property",
        "email",
        "phone",
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
        "id_upload_link",
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
        ("Identification", {
            "fields": (
                "drivers_license_number",
                "has_valid_odl",
                "oregon_id_number",
                "id_upload",
                "id_upload_link",
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
            "classes": ("collapse",),
            "fields": (
                "additional_notes",
                "created_at",
            )
        }),
    )

    def id_upload_link(self, obj):
        if obj and obj.id_upload:
            return format_html(
                '<a href="{}" target="_blank">View uploaded ID / ODL</a>',
                obj.id_upload.url
            )
        return "No ID uploaded"

    id_upload_link.short_description = "Uploaded ID / ODL"

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [field.name for field in self.model._meta.fields] + ["id_upload_link"]
        return self.readonly_fields


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
