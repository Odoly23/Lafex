from django.contrib import admin

from .models import Entitlement, Plan, UsageDay, Voucher


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
	list_display = ('code', 'label', 'hours', 'price_usd', 'active', 'sort')


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
	list_display = ('code', 'plan', 'used_by', 'used_at', 'created_at')
	list_filter = ('plan', 'used_at')
	search_fields = ('code', 'used_by__email')


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
	list_display = ('user', 'expires_at')
	search_fields = ('user__email',)


admin.site.register(UsageDay)
