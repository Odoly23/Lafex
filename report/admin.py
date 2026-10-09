from django.contrib import admin

from .models import MonitorLog


@admin.register(MonitorLog)
class MonitorLogAdmin(admin.ModelAdmin):
	list_display = ('viewer', 'session', 'viewed_at')
	search_fields = ('viewer__email', 'session__user__email')
