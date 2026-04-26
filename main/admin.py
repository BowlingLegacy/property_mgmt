from django.contrib import admin
from .models import Property, User, HousingApplication


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "role", "invite_code")
    list_filter = ("role",)
    search_fields = ("username", "email", "invite_code")


@admin.register(HousingApplication)
class HousingApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "phone", "monthly_income", "created_at")
    search_fields = ("full_name", "email", "phone")
    list_filter = ("created_at",)
