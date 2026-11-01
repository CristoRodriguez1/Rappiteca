from django.urls import path

from . import views

urlpatterns = [
    path('admin-fines/', views.admin_fine_list, name='fines_admin_list'),
]
