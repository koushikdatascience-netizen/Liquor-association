from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .backends import normalize_mobile
from .models import Profile


class ApplicantRegistrationForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    mobile_number = forms.CharField(max_length=15, help_text="Use this number for login and notifications.")

    class Meta:
        model = User
        fields = ["email", "mobile_number"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_mobile_number(self):
        mobile_number = normalize_mobile(self.cleaned_data["mobile_number"])
        if len(mobile_number) < 10:
            raise forms.ValidationError("Enter a valid mobile number.")
        existing_profiles = Profile.objects.exclude(mobile_number="")
        for profile in existing_profiles:
            existing_mobile = normalize_mobile(profile.mobile_number)
            if existing_mobile == mobile_number or existing_mobile.endswith(mobile_number[-10:]):
                raise forms.ValidationError("An account with this mobile number already exists.")
        if Profile.objects.filter(mobile_number=mobile_number).exists():
            raise forms.ValidationError("An account with this mobile number already exists.")
        return mobile_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        user.set_unusable_password()
        if commit:
            user.save()
            user.profile.mobile_number = self.cleaned_data["mobile_number"]
            user.profile.save()
        return user


class MemberLoginRequestForm(forms.Form):
    identifier = forms.CharField(
        label="Email or mobile number",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )


class UnifiedAuthForm(forms.Form):
    """Single entry point for both login and registration (email + mobile)."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
    )
    mobile_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "10-digit mobile number"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_mobile_number(self):
        mobile = normalize_mobile(self.cleaned_data["mobile_number"])
        if len(mobile) < 10:
            raise forms.ValidationError("Enter a valid mobile number.")
        return mobile


class AdminAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Admin username or email",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(
                "This password login is only for administrators. Members must use OTP login.",
                code="not_staff",
            )


class OTPVerificationForm(forms.Form):
    otp = forms.CharField(label="OTP", max_length=10, widget=forms.TextInput(attrs={"autocomplete": "one-time-code"}))
