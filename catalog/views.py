from django.shortcuts import render

from accounts.models import User


def home(request):
    current_user = None
    user_id = request.session.get('user_id')

    if user_id:
        try:
            current_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # Session points to a user that no longer exists — clear it out.
            request.session.flush()

    return render(request, 'home.html', {'current_user': current_user})