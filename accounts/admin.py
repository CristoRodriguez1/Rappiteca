from django.contrib import admin

from .models import User, Notification


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_name', 'email', 'role')
    search_fields = ('name', 'last_name', 'email')
    list_filter = ('role',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    list_filter = ('notification_type', 'is_read', 'created_at')
    readonly_fields = ('created_at',)