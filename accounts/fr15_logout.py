"""
FR-15 Logout requirement.

IF a user selects the logout option THEN THE Rappiteca system SHALL end the
user's session within 3 seconds.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


@require_http_methods(['GET', 'POST'])
def end_session_view(request):
    """
    FR-15: End the active session immediately and confirm logout to the user.
    Supports GET (link) and POST (form) so logout works from any entry point.
    """
    if request.method == 'POST':
        request.session.flush()
        messages.success(request, 'You have been logged out.')
        return redirect('home')

    if not request.session.get('user_id'):
        messages.info(request, 'You are not logged in.')
        return redirect('home')

    return render(request, 'fr15_logout_confirm.html')


@require_http_methods(['POST'])
def confirm_end_session_view(request):
    """FR-15: Process logout confirmation and end the session."""
    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('home')
