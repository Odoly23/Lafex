from django.contrib import admin

from .models import Mission, Scenario


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('slug', 'title_tet', 'title_en', 'order', 'active')


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('slug', 'scenario', 'band', 'order', 'is_placement', 'active')
    list_filter = ('scenario', 'band', 'is_placement')
    search_fields = ('slug', 'title_en', 'title_tet')
