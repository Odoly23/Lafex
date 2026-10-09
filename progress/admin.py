from django.contrib import admin

from .models import Activity, Certificate


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
	list_display = ('user', 'kind', 'points', 'ref', 'created_at')
	list_filter = ('kind',)
	search_fields = ('user__email',)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
	list_display = ('code', 'user', 'level', 'name', 'issued_at')
	search_fields = ('code', 'user__email', 'name')
