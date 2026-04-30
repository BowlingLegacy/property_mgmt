from django.contrib import admin
from .models import Property, PropertyImage, HousingApplication, ApplicantDocument, BlogPost


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


class ApplicantDocumentInline(admin.TabularInline):
    model = ApplicantDocument
    extra = 0
    fields = (
        "name",
        "document_type",
        "file",
        "status",
        "needs_signature",
        "needs_initials",
        "locked",
        "created_at",
    )
    readonly_fields = ("created_at",)


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
    list_display = ("full_name", "email", "phone", "property", "created_at")
    search_fields = ("full_name", "email", "phone")
    list_filter = ("property", "created_at")


@admin.register(ApplicantDocument)
class ApplicantDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "application", "document_type", "status", "created_at")
    list_filter = ("document_type", "status", "created_at")
    search_fields = ("name", "application__full_name")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "created_at")
    list_filter = ("published",)
