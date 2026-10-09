from django.contrib import admin

from .models import VocabCategory, VocabItem

admin.site.register(VocabCategory)


@admin.register(VocabItem)
class VocabItemAdmin(admin.ModelAdmin):
	list_display = ('tet', 'en', 'category', 'active')
	list_filter = ('category',)
	search_fields = ('tet', 'en')
