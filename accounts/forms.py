from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

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
        mobile_number = self.cleaned_data["mobile_number"].strip()
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
