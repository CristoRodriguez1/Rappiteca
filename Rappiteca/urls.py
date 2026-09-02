"""
URL configuration for Rappiteca project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from catalog import views
from accounts import views as accounts_views
from accounts import fr15_logout as fr15_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('signup/', accounts_views.signup_view, name='signup'),
    path('login/', accounts_views.login_view, name='login'),
    path('logout/', accounts_views.logout_view, name='logout'),

    path('libro/<int:book_id>/', views.detalle_libro, name='detalle_libro'),
    path('reservar/<int:book_id>/', views.reservar_libro, name='reservar_libro'),
    path('cancelar-reserva/<int:loan_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('admin-prestamos/', views.gestionar_loans, name='gestionar_prestamos'),
    path('admin-prestamos/<int:loan_id>/recogido/', views.marcar_recogido, name='marcar_recogido'),
    path('admin-prestamos/<int:loan_id>/devuelto/', views.marcar_devuelto, name='marcar_devuelto'),
    path('admin-inventario/', views.ver_inventario, name='ver_inventario'),
    path('admin-inventario/<int:book_id>/quitar/', views.eliminar_libro, name='eliminar_libro'),
    path('admin-inventario/agregar/', views.agregar_libro, name='agregar_libro'),

    # FR-16 Display borrowers information
    path('', include('catalog.fr16_urls')),

    path('loans/', include('loans.urls')),
    # FR-15 Logout (specific paths before accounts.urls include)
    path('accounts/end-session/', fr15_views.end_session_view, name='fr15_end_session'),
    path('accounts/end-session/confirm/', fr15_views.confirm_end_session_view, name='fr15_confirm_end_session'),
    path('accounts/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
