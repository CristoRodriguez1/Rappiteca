from django.urls import path

from . import fr15_logout

urlpatterns = [
    path('end-session/', fr15_logout.end_session_view, name='fr15_end_session'),
    path('end-session/confirm/', fr15_logout.confirm_end_session_view, name='fr15_confirm_end_session'),
]
