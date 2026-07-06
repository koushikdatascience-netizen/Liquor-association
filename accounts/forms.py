from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .backends import normalize_mobile
from .models import Profile


class ApplicantRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    mobile_number = forms.CharField(max_length=15, help_text="Use this number for login and notifications.")

    class Meta:
        model = User
        fields = ["email", "mobile_number", "password1", "password2"]

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
        if commit:
            user.save()
            user.profile.mobile_number = self.cleaned_data["mobile_number"]
            user.profile.save()
        return user


class EmailOrMobileAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or mobile number",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )


class OTPVerificationForm(forms.Form):
    email_otp = forms.CharField(label="Email OTP", max_length=10)
    mobile_otp = forms.CharField(label="WhatsApp/Mobile OTP", max_length=10)
