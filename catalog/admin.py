from django.contrib import admin
from .models import Book, BookAvailabilityAlert
from loans.models import Loan


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'total_copies', 'available_copies')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('category',)


@admin.register(BookAvailabilityAlert)
class BookAvailabilityAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at', 'is_active')
    search_fields = ('user__email', 'book__title')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'status', 'reservation_date', 'pickup_date', 'return_date', 'renewals')
    list_filter = ('status',)
