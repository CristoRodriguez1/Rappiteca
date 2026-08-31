from django import forms
from django.contrib.auth.hashers import check_password, make_password

from .models import User


class SignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'At least 8 characters'}),
        label='Password',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Re-enter your password'}),
        label='Confirm password',
    )

    class Meta:
        model = User
        fields = ['name', 'last_name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Jane'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Doe'}),
            'email': forms.EmailInput(attrs={'placeholder': 'jane.doe@university.edu'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = make_password(self.cleaned_data['password'])  # hashed, not plain text
        user.role = 'stu'  # default role — role is never taken from the form
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'jane.doe@university.edu'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Your password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user = None

            # Same error for "no user" and "wrong password" on purpose —
            # doesn't reveal which part was wrong.
            if user is None or not check_password(password, user.password):
                raise forms.ValidationError('Invalid email or password.')

            self.user = user  # stash the matched user so the view can log them in

        return cleaned_data