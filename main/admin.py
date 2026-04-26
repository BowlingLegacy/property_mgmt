from django.contrib import admin
from .models import Property, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 3


class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]


admin.site.register(Property, PropertyAdmin)
