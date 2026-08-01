from django import forms
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
        user.password = self.cleaned_data['password']  # stored as plain text — MVP only
        user.role = 'stu'  # default role — role is never taken from the form
        if commit:
            user.save()
        return user