from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import SignupForm


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