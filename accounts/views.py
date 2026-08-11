from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import LoginForm, SignupForm


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