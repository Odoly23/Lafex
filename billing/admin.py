from django.contrib import admin

from .models import Entitlement, Plan, RedeemAttempt, UsageDay, Voucher, VoucherBatch


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
	list_display = ('code', 'label', 'hours', 'price_usd', 'active', 'sort')


@admin.register(VoucherBatch)
class VoucherBatchAdmin(admin.ModelAdmin):
	list_display = ('id', 'label', 'plan', 'quantity', 'created_by', 'created_at', 'valid_until', 'voided_at')
	readonly_fields = ('quantity', 'created_by', 'created_at')


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
	"""Hanya baca: kode rahasia tidak disimpan, jadi voucher tidak bisa dibuat/diubah manual lewat sini."""
	list_display = ('serial', 'plan', 'batch', 'status', 'used_by', 'used_at')
	list_filter = ('plan',)
	search_fields = ('serial', 'used_by__email')

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
	list_display = ('user', 'expires_at')
	search_fields = ('user__email',)


admin.site.register(UsageDay)
admin.site.register(RedeemAttempt)
