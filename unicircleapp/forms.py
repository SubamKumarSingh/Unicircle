# unicircleapp/forms.py
from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
import re
# if validate function in same file adjust import

User = get_user_model()

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        required=True,
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        required=True,
    )
    new_password_conf = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        required=True,
    )

    def __init__(self, user=None, *args, **kwargs):
        """
        pass request.user as `user` when instantiating so we can check current password
        """
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        cur = self.cleaned_data.get("current_password", "")
        if not self.user:
            raise ValidationError("User is required.")
        if not self.user.check_password(cur):
            raise ValidationError("Current password is incorrect.")
        return cur

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        conf = cleaned.get("new_password_conf")
        cur = cleaned.get("current_password")

        if new and conf and new != conf:
            self.add_error("new_password_conf", ValidationError("New password and confirmation do not match."))

        if cur and new and cur == new:
            self.add_error("new_password", ValidationError("New password must be different from current password."))

        # run your custom criteria validator on the new password
        if new and not self.errors.get("new_password"):
            try:
                # call your existing validator (adjust import path if needed)
                validate_password_criteria(new)
            except ValidationError as e:
                self.add_error("new_password", e)

        return cleaned
# User = get_user_model()

def validate_password_criteria(password):
    if not password:
        raise ValidationError("Password is required.")
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if " " in password:
        raise ValidationError("Password must not contain spaces.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValidationError("Password must include at least one letter and one digit.")

class SocialSignupForm(forms.Form):
    username = forms.CharField(max_length=150, label="Username", required=True)
    password = forms.CharField(widget=forms.PasswordInput, label="Password", required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password", required=True)

    # Prefilled read-only fields from provider (optional)
    email = forms.EmailField(
        required=False,
        label="Email (from Google)",
        widget=forms.EmailInput(attrs={'readonly': 'readonly'})
    )
    first_name = forms.CharField(
        max_length=30, required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        label="First Name"
    )
    last_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        label="Last Name"
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise ValidationError("Username is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        validate_password_criteria(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('confirm_password')

        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")

        # Email uniqueness check (use initial value if readonly not posted)
        email = cleaned.get('email') or self.fields['email'].initial
        if email and User.objects.filter(email__iexact=email).exists():
            self.add_error('email', "An account with this email already exists. Try logging in instead.")

        return cleaned


# ------------------------
# Login Form
# ------------------------
class LoginForm(forms.Form):
    login_username = forms.CharField(max_length=150, required=True, label="Username")
    login_password = forms.CharField(widget=forms.PasswordInput, required=True, label="Password")

    def clean_login_username(self):
        username = self.cleaned_data.get('login_username', '').strip()
        if not username:
            raise ValidationError("Please enter your username.")
        if not User.objects.filter(username=username).exists():
            raise ValidationError("No account found with this username.")
        return username

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("login_username")
        password = cleaned.get("login_password")

        # Only attempt authentication if username exists
        if username and password and not self.errors.get("login_username"):
            user = authenticate(username=username, password=password)
            if not user:
                self.add_error("login_password", "Invalid password.")
        return cleaned
