from django.contrib import messages
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .backends import EmailOrMobileBackend
from .forms import AdminAuthenticationForm, ApplicantRegistrationForm, MemberLoginRequestForm, OTPVerificationForm, UnifiedAuthForm
from .models import OTPVerification, Profile
from .services import send_login_otps, send_registration_otps

import socket


class AdminLoginView(auth_views.LoginView):
    template_name = "accounts/admin_login.html"
    authentication_form = AdminAuthenticationForm
    next_page = "staff_dashboard"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff:
                return redirect(self.get_success_url())
            auth_logout(request)
            messages.info(request, "Please sign in with an administrator account.")
        return super().dispatch(request, *args, **kwargs)


def otp_delivery_message(result):
    sent = set((result or {}).get("sent", []))
    errors = (result or {}).get("errors", [])
    if "email" in sent and "whatsapp" in sent:
        return "We sent an OTP to your email and WhatsApp."
    if "whatsapp" in sent:
        return "We sent an OTP to your WhatsApp. Email delivery failed, but you can continue with the WhatsApp OTP."
    if "email" in sent:
        return "We sent an OTP to your email."
    if errors:
        return "OTP was generated. Please check your messages or resend OTP."
    return "We sent an OTP."


def test_smtp_connection(request):
    import socket
    from django.http import JsonResponse

    hosts = {
        "hostinger_465": ("smtp.hostinger.com", 465),
        "hostinger_587": ("smtp.hostinger.com", 587),
        "brevo_587": ("smtp-relay.brevo.com", 587),
    }

    results = {}

    for name, target in hosts.items():
        try:
            sock = socket.create_connection(target, timeout=10)
            sock.close()
            results[name] = "CONNECTED"
        except Exception as e:
            results[name] = f"{type(e).__name__}: {str(e)}"

    return JsonResponse(results)


def pending_otps(user, purpose):
    return OTPVerification.objects.filter(
        user=user,
        purpose=purpose,
        verified_at__isnull=True,
    ).order_by("-created_at")


def verify_any_pending_otp(user, purpose, code):
    for otp in pending_otps(user, purpose):
        if otp.verify(code):
            return True
    return False


def find_member_user(identifier):
    user = EmailOrMobileBackend().get_user_by_identifier(identifier)
    if not user or not user.is_active:
        return None
    return user


def register(request):
    if request.user.is_authenticated:
        return redirect("staff_dashboard" if request.user.is_staff else "member_dashboard")

    if request.method == "POST":
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="accounts.backends.EmailOrMobileBackend")
            request.session["registration_otp_user_id"] = user.pk
            try:
                delivery_result = send_registration_otps(user)
                messages.success(request, f"Account created. {otp_delivery_message(delivery_result)}")
            except Exception as exc:
                messages.warning(request, f"Account created, but OTP sending failed: {exc}")
            return redirect("member_dashboard")
        messages.error(request, "Registration was not completed. Please fix the highlighted fields.")
    else:
        form = ApplicantRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def verify_registration_otp(request):
    user_id = request.session.get("registration_otp_user_id")
    if request.user.is_authenticated:
        user = request.user
    else:
        user = find_member_user_by_id(user_id)
    if user is None:
        messages.error(request, "Please register before verifying OTP.")
        return redirect("register")

    profile = user.profile
    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            if verify_any_pending_otp(user, OTPVerification.Purpose.REGISTRATION, form.cleaned_data["otp"]):
                profile.email_verified = True
                profile.mobile_verified = True
                profile.save(update_fields=["email_verified", "mobile_verified"])
                login(request, user, backend="accounts.backends.EmailOrMobileBackend")
                request.session.pop("registration_otp_user_id", None)
                messages.success(request, "OTP verified. You can now submit your membership application from the dashboard.")
                return redirect("member_dashboard")
            messages.error(request, "Invalid or expired OTP. Please try again or resend OTP.")
    else:
        form = OTPVerificationForm()
    return render(
        request,
        "accounts/verify_otp.html",
        {
            "form": form,
            "title": "Verify Registration OTP",
            "heading": "Verify OTP",
            "subheading": "Confirm account",
            "button_label": "Verify Account",
            "resend_url": reverse("resend_registration_otp"),
        },
    )


def resend_registration_otp(request):
    user = request.user if request.user.is_authenticated else find_member_user_by_id(request.session.get("registration_otp_user_id"))
    if user is None:
        messages.error(request, "Please register before requesting another OTP.")
        return redirect("register")
    try:
        delivery_result = send_registration_otps(user)
        messages.success(request, otp_delivery_message(delivery_result))
    except Exception as exc:
        messages.error(request, f"Could not send OTP: {exc}")
    return redirect("verify_registration_otp")


def find_member_user_by_id(user_id):
    if not user_id:
        return None
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None
    return EmailOrMobileBackend().get_user(user_id)


def find_user_by_email_or_mobile(email, mobile):
    user = User.objects.filter(email__iexact=email).first()
    if user:
        return user
    profile = Profile.objects.filter(mobile_number=mobile).first()
    return profile.user if profile else None


def login_request_otp(request):
    if request.user.is_authenticated:
        return redirect("staff_dashboard" if request.user.is_staff else "member_dashboard")

    if request.method == "POST":
        form = UnifiedAuthForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            mobile = form.cleaned_data["mobile_number"]
            user = find_user_by_email_or_mobile(email, mobile)
            if user and user.is_staff:
                messages.error(request, "Admins must use password login.")
                return redirect("admin_login")
            if user:
                purpose = OTPVerification.Purpose.LOGIN
                send_otps = send_login_otps
            else:
                user = User(email=email, username=email)
                user.set_unusable_password()
                user.save()
                user.profile.mobile_number = mobile
                user.profile.save()
                purpose = OTPVerification.Purpose.REGISTRATION
                send_otps = send_registration_otps
            try:
                delivery_result = send_otps(user)
            except Exception as exc:
                messages.error(request, f"Could not send OTP: {exc}")
                return redirect("login")
            request.session["auth_otp_user_id"] = user.pk
            request.session["auth_otp_is_registration"] = (purpose == OTPVerification.Purpose.REGISTRATION)
            messages.success(request, otp_delivery_message(delivery_result))
            return redirect("login_verify_otp")
    else:
        form = UnifiedAuthForm()
    return render(request, "accounts/login.html", {"form": form})


def login_verify_otp(request):
    if request.user.is_authenticated:
        return redirect("staff_dashboard" if request.user.is_staff else "member_dashboard")

    user = find_member_user_by_id(request.session.get("auth_otp_user_id"))
    if user is None:
        messages.error(request, "Please request an OTP first.")
        return redirect("login")
    if user.is_staff:
        messages.error(request, "Admins must use password login.")
        request.session.pop("auth_otp_user_id", None)
        return redirect("admin_login")

    is_registration = request.session.get("auth_otp_is_registration", False)
    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            purpose = OTPVerification.Purpose.REGISTRATION if is_registration else OTPVerification.Purpose.LOGIN
            if verify_any_pending_otp(user, purpose, form.cleaned_data["otp"]):
                profile = user.profile
                profile.email_verified = True
                profile.mobile_verified = True
                profile.save(update_fields=["email_verified", "mobile_verified"])
                login(request, user, backend="accounts.backends.EmailOrMobileBackend")
                request.session.pop("auth_otp_user_id", None)
                request.session.pop("auth_otp_is_registration", None)
                messages.success(request, "You are signed in.")
                return redirect("member_dashboard")
            messages.error(request, "Invalid or expired OTP. Please try again or request a new one.")
    else:
        form = OTPVerificationForm()
    return render(
        request,
        "accounts/verify_otp.html",
        {
            "form": form,
            "title": "Verify OTP",
            "heading": "Enter OTP",
            "subheading": "Secure access",
            "button_label": "Verify & Continue",
            "resend_url": reverse("login_resend_otp"),
        },
    )


def login_resend_otp(request):
    user = find_member_user_by_id(request.session.get("auth_otp_user_id"))
    if user is None:
        messages.error(request, "Please request an OTP first.")
        return redirect("login")
    if user.is_staff:
        messages.error(request, "Admins must use password login.")
        request.session.pop("auth_otp_user_id", None)
        return redirect("admin_login")
    is_registration = request.session.get("auth_otp_is_registration", False)
    try:
        if is_registration:
            delivery_result = send_registration_otps(user)
        else:
            delivery_result = send_login_otps(user)
        messages.success(request, otp_delivery_message(delivery_result))
    except Exception as exc:
        messages.error(request, f"Could not send OTP: {exc}")
    return redirect("login_verify_otp")
