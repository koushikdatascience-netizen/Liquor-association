from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailOrMobileAuthenticationForm
from .views import register, resend_registration_otp, verify_registration_otp

urlpatterns = [
    path("register/", register, name="register"),
    path("verify-otp/", verify_registration_otp, name="verify_registration_otp"),
    path("resend-otp/", resend_registration_otp, name="resend_registration_otp"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailOrMobileAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
