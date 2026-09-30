"""
FR-21 User profile display.

IF a user accesses their profile section THEN THE Rappiteca system SHOULD
display the user's personal information within 3 seconds.
"""

from django.shortcuts import redirect, render

from .views import _usuario_actual

ROLE_LABELS = {
    'stu': 'Student',
    'adm': 'Administrator',
}


def profile_view(request):
    current_user = _usuario_actual(request)
    if not current_user:
        return redirect('login')

    initials = f'{current_user.name[:1]}{current_user.last_name[:1]}'.upper()

    contexto = {
        'current_user': current_user,
        'full_name': f'{current_user.name} {current_user.last_name}'.strip(),
        'initials': initials,
        'role_label': ROLE_LABELS.get(current_user.role, current_user.role),
    }
    return render(request, 'fr21_profile.html', contexto)
