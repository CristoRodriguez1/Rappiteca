from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import LoginForm, SignupForm
from .models import Notification, User


def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully.')
            return redirect('/')
    else:
        form = SignupForm()

    return render(request, 'signupview.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.user
            request.session['user_id'] = user.id
            request.session['user_role'] = user.role
            messages.success(request, f'Welcome back, {user.name}!')
            if user.role == 'adm':
                return redirect('gestionar_prestamos')
            return redirect('/')
    else:
        form = LoginForm()

    return render(request, 'loginview.html', {'form': form})


def logout_view(request):
    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('/')


def _usuario_actual(request):
    current_user = None
    user_id = request.session.get('user_id')

    if user_id:
        try:
            current_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # Session points to a user that no longer exists — clear it out.
            request.session.flush()

    return current_user


def notifications_view(request):
    current_user = _usuario_actual(request)
    if not current_user:
        return redirect('login')
    
    notifications = Notification.objects.filter(user=current_user).order_by('-created_at')
    
    contexto = {
        'current_user': current_user,
        'notifications': notifications,
    }
    return render(request, 'notifications.html', contexto)


def mark_notification_read(request, notification_id):
    current_user = _usuario_actual(request)
    if not current_user:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        notification = Notification.objects.get(id=notification_id, user=current_user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)


def mark_all_notifications_read(request):
    current_user = _usuario_actual(request)
    if not current_user:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    Notification.objects.filter(user=current_user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


def notification_count(request):
    current_user = _usuario_actual(request)
    if not current_user:
        return JsonResponse({'count': 0})
    
    unread_count = Notification.objects.filter(user=current_user, is_read=False).count()
    return JsonResponse({'count': unread_count})