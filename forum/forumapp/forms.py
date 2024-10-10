from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)  # Add an email field

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')  # Include the fields you want in the sign-up form
