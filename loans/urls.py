from django.urls import path
from . import views
from . import fr22_history

urlpatterns = [
    path('mis-prestamos/', views.user_loans, name='user_loans'),
    path('historial/', fr22_history.loan_history, name='loan_history'),
    path('devolver/<int:loan_id>/', views.solicitar_devolucion, name='solicitar_devolucion'),
    path('renovar/<int:loan_id>/', views.renovar_prestamo, name='renovar_prestamo'),
]
