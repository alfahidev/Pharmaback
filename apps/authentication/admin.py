from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.authentication.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "pharmacy", "phone", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "pharmacy")
    search_fields = ("username", "email", "phone", "pharmacy__name")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Officine & Rôle SaaS", {"fields": ("pharmacy", "role", "phone")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Officine & Rôle SaaS", {"fields": ("pharmacy", "role", "phone")}),
    )
