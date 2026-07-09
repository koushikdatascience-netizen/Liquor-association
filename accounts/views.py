from django.contrib import messages
from django.contrib.auth import login
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .backends import EmailOrMobileBackend
from .forms import ApplicantRegistrationForm, MemberLoginRequestForm, OTPVerificationForm
from .models import OTPVerification
from .services import send_login_otps, send_registration_otps

import socket


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
    if request.method == "POST":
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                send_registration_otps(user)
                messages.success(request, "Account created. We sent an OTP to your email and WhatsApp.")
            except Exception as exc:
                messages.warning(request, f"Account created, but OTP sending failed: {exc}")
            request.session["registration_otp_user_id"] = user.pk
            return redirect("verify_registration_otp")
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
                messages.success(request, "OTP verified. You can now submit your membership application.")
                return redirect("application_create")
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
        send_registration_otps(user)
        messages.success(request, "A new OTP has been sent to your email and WhatsApp.")
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


def login_request_otp(request):
    if request.user.is_authenticated:
        return redirect("staff_dashboard" if request.user.is_staff else "member_dashboard")

    if request.method == "POST":
        form = MemberLoginRequestForm(request.POST)
        if form.is_valid():
            user = find_member_user(form.cleaned_data["identifier"])
            if user and user.is_staff:
                messages.error(request, "Admins must use password login.")
                return redirect("admin_login")
            if user:
                try:
                    send_login_otps(user)
                    request.session["login_otp_user_id"] = user.pk
                    messages.success(request, "We sent an OTP to your email and WhatsApp.")
                    return redirect("login_verify_otp")
                except Exception as exc:
                    messages.error(request, f"Could not send OTP: {exc}")
            else:
                messages.error(request, "No active member account was found for that email or mobile number.")
    else:
        form = MemberLoginRequestForm()
    return render(request, "accounts/login.html", {"form": form})


def login_verify_otp(request):
    if request.user.is_authenticated:
        return redirect("staff_dashboard" if request.user.is_staff else "member_dashboard")

    user = find_member_user_by_id(request.session.get("login_otp_user_id"))
    if user is None:
        messages.error(request, "Please request a login OTP first.")
        return redirect("login")
    if user.is_staff:
        messages.error(request, "Admins must use password login.")
        request.session.pop("login_otp_user_id", None)
        return redirect("admin_login")

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            if verify_any_pending_otp(user, OTPVerification.Purpose.LOGIN, form.cleaned_data["otp"]):
                login(request, user, backend="accounts.backends.EmailOrMobileBackend")
                request.session.pop("login_otp_user_id", None)
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
            "title": "Verify Login OTP",
            "heading": "Enter OTP",
            "subheading": "Secure login",
            "button_label": "Sign in",
            "resend_url": reverse("login_resend_otp"),
        },
    )


def login_resend_otp(request):
    user = find_member_user_by_id(request.session.get("login_otp_user_id"))
    if user is None:
        messages.error(request, "Please request a login OTP first.")
        return redirect("login")
    if user.is_staff:
        messages.error(request, "Admins must use password login.")
        request.session.pop("login_otp_user_id", None)
        return redirect("admin_login")
    try:
        send_login_otps(user)
        messages.success(request, "A new OTP has been sent to your email and WhatsApp.")
    except Exception as exc:
        messages.error(request, f"Could not send OTP: {exc}")
    return redirect("login_verify_otp")
