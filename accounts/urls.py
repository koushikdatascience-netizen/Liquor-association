from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import AdminAuthenticationForm
from .views import (
    login_request_otp,
    login_resend_otp,
    login_verify_otp,
    register,
    resend_registration_otp,
    verify_registration_otp,
    test_smtp_connection,
)

urlpatterns = [
    path("register/", register, name="register"),
    path("verify-otp/", verify_registration_otp, name="verify_registration_otp"),
    path("resend-otp/", resend_registration_otp, name="resend_registration_otp"),
    path("login/", login_request_otp, name="login"),
    path("login/verify-otp/", login_verify_otp, name="login_verify_otp"),
    path("login/resend-otp/", login_resend_otp, name="login_resend_otp"),
    path(
        "admin-login/",
        auth_views.LoginView.as_view(
            template_name="accounts/admin_login.html",
            authentication_form=AdminAuthenticationForm,
            redirect_authenticated_user=True,
            next_page="staff_dashboard",
        ),
        name="admin_login",
    ),

    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path(
        "test-smtp/",
        test_smtp_connection,
        name="test_smtp_connection",
    ),
]
