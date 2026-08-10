from django.urls import path
from . import views
 
urlpatterns = [
    path('', views.home, name='home'),
    path('reservar/<int:book_id>/', views.reservar_libro, name='reservar_libro'),
 
    path('admin-prestamos/', views.gestionar_prestamos, name='gestionar_prestamos'),
    path('admin-prestamos/<int:prestamo_id>/recogido/', views.marcar_recogido, name='marcar_recogido'),
    path('admin-prestamos/<int:prestamo_id>/devuelto/', views.marcar_devuelto, name='marcar_devuelto'),
]