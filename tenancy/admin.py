from django.contrib import admin
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price", "duration_days", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


class TenantSubscriptionInline(admin.StackedInline):
    model = TenantSubscription
    extra = 0
    can_delete = False


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "city", "phone", "is_active", "created_at")
    list_filter = ("is_active", "city")
    search_fields = ("id", "name", "code", "license_number", "phone")
    inlines = [TenantSubscriptionInline]


@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "plan", "status", "start_date", "end_date", "is_active")
    list_filter = ("status", "is_active", "plan")
    search_fields = ("tenant__name", "tenant__id", "notes")
