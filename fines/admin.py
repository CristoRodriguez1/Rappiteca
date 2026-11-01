from django.contrib import admin

from .models import Fine


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ('user', 'loan', 'days_overdue', 'amount', 'status', 'is_final', 'applied_at')
    list_filter = ('status', 'is_final')
    search_fields = ('user__email', 'loan__book__title')
