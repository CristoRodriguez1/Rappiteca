from django.contrib import admin
from .models import Book, Prestamo


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'total_copies', 'available_copies')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('category',)


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'estado', 'fecha_reserva', 'fecha_recogida', 'fecha_devolucion')
    list_filter = ('estado',)
