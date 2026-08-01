from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_name', 'email', 'role')
    search_fields = ('name', 'last_name', 'email')
    list_filter = ('role',)