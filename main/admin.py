from django.contrib import admin
from .models import Property, PropertyImage, HousingApplication, BlogPost


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
    list_display = ("name", "address")


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("property", "caption")


@admin.register(HousingApplication)
class HousingApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "property", "created_at")
    search_fields = ("full_name", "email", "phone")
    list_filter = ("property", "created_at")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "created_at")
    list_filter = ("published",)
