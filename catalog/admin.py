from django.contrib import admin
from .models import Book
from loans.models import Loan


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'total_copies', 'available_copies')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('category',)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'status', 'reservation_date', 'pickup_date', 'return_date', 'renewals')
    list_filter = ('status',)
