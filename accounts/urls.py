from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailOrMobileAuthenticationForm
from .views import register

urlpatterns = [
    path("register/", register, name="register"),
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
