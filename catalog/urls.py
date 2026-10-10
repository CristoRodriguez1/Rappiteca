from django.urls import path
from . import views
 
urlpatterns = [
    path('', views.home, name='home'),
    path('libro/<int:book_id>/', views.detalle_libro, name='detalle_libro'),
    path('reservar/<int:book_id>/', views.reservar_libro, name='reservar_libro'),
    path('cancelar/<int:loan_id>/', views.cancelar_reserva, name='cancelar_reserva'),

    path('admin-prestamos/', views.gestionar_loans, name='gestionar_prestamos'),
    path('admin-prestamos/<int:loan_id>/recogido/', views.marcar_recogido, name='marcar_recogido'),
    path('admin-prestamos/<int:loan_id>/devuelto/', views.marcar_devuelto, name='marcar_devuelto'),

    path('admin-inventario/', views.ver_inventario, name='ver_inventario'),
    path('admin-inventario/agregar/', views.agregar_libro, name='agregar_libro'),
    path('admin-inventario/<int:book_id>/eliminar/', views.eliminar_libro, name='eliminar_libro'),
]
