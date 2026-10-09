from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class LafexUserAdmin(UserAdmin):
    ordering = ('-date_joined',)
    list_display = ('email', 'level', 'placement_done', 'is_staff', 'date_joined')
    search_fields = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Lafex', {'fields': ('name', 'level', 'placement_done')}),
        ('Izin', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2')}),)
