from django.urls import path

from . import views

urlpatterns = [
    path('admin-fines/', views.admin_fine_list, name='fines_admin_list'),
    path('my-fines/', views.user_fine_list, name='fines_user_list'),
    path('request-payment/<int:fine_id>/', views.request_payment, name='fine_request_payment'),
    path('confirm-payment/<int:fine_id>/', views.confirm_payment, name='fine_confirm_payment'),
    path('confirm-in-person/<int:fine_id>/', views.confirm_in_person_payment, name='fine_confirm_in_person'),
]
