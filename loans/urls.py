from django.urls import path
from . import views

urlpatterns = [
    path('mis-prestamos/', views.user_loans, name='user_loans'),
]