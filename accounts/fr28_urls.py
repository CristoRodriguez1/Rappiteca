from django.urls import path

from . import fr28_users

urlpatterns = [
    path('admin-users/', fr28_users.admin_user_list, name='fr28_user_list'),
    path('admin-users/<int:user_id>/', fr28_users.admin_user_detail, name='fr28_user_detail'),
]
