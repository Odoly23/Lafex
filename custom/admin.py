from django.contrib import admin

from .models import Municipality


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
	list_display = ('name', 'code', 'hckey')
	search_fields = ('name', 'code', 'hckey')
