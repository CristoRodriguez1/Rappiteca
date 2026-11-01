from django import forms
from django.contrib import admin
from .audit import log_action
from .models import AuditLog, Book, BookAvailabilityAlert
from loans.models import Loan


ACTIVE_LOAN_STATUSES = [Loan.STATUS_RESERVED, Loan.STATUS_BORROWED]


def copies_in_use(book):
    """Copias que están reservadas o prestadas ahora mismo."""
    return Loan.objects.filter(book=book, status__in=ACTIVE_LOAN_STATUSES).count()


class BookAdminForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = '__all__'

    def clean_total_copies(self):
        total = self.cleaned_data['total_copies']
        if total < 1:
            raise forms.ValidationError('A book must have at least one copy.')
        if self.instance.pk:
            in_use = copies_in_use(self.instance)
            if total < in_use:
                raise forms.ValidationError(
                    f'Cannot set fewer copies than are currently reserved or borrowed ({in_use}).'
                )
        return total


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookAdminForm
    list_display = ('title', 'author', 'category', 'total_copies', 'available_copies')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('category',)
    # Se calcula a partir de total_copies y los préstamos activos; no se edita a mano.
    readonly_fields = ('available_copies',)

    # Cambios de inventario hechos desde el panel de Django: no pasan por
    # views.py, así que se registran aquí.
    def save_model(self, request, obj, form, change):
        # Mantener available_copies coherente con total_copies:
        # disponibles = total - (reservadas + prestadas).
        if not change:
            obj.available_copies = obj.total_copies
        elif 'total_copies' in form.changed_data:
            obj.available_copies = obj.total_copies - copies_in_use(obj)

        super().save_model(request, obj, form, change)
        if change:
            changed = ', '.join(form.changed_data) or 'no fields'
            log_action(
                request, AuditLog.ACTION_BOOK_UPDATED,
                f'Edited "{obj.title}" (changed: {changed})',
                via_django_admin=True,
            )
        else:
            log_action(
                request, AuditLog.ACTION_BOOK_ADDED,
                f'Added "{obj.title}" to inventory ({obj.total_copies} copies)',
                via_django_admin=True,
            )

    def delete_model(self, request, obj):
        titulo = obj.title
        super().delete_model(request, obj)
        log_action(
            request, AuditLog.ACTION_BOOK_REMOVED,
            f'Removed "{titulo}" from inventory',
            via_django_admin=True,
        )

    def delete_queryset(self, request, queryset):
        # Borrado en lote desde la lista ("Delete selected books").
        titulos = list(queryset.values_list('title', flat=True))
        super().delete_queryset(request, queryset)
        for titulo in titulos:
            log_action(
                request, AuditLog.ACTION_BOOK_REMOVED,
                f'Removed "{titulo}" from inventory',
                via_django_admin=True,
            )


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


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'admin_email', 'action', 'description')
    list_filter = ('action',)
    search_fields = ('admin_email', 'description')
    readonly_fields = ('admin', 'admin_email', 'action', 'description', 'created_at')

    # El log solo se consulta: nadie lo crea, edita ni borra a mano.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
