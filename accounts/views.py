from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ApplicantRegistrationForm, OTPVerificationForm
from .models import OTPVerification
from .services import send_registration_otps


def pending_otp(user, channel):
    return OTPVerification.objects.filter(
        user=user,
        channel=channel,
        purpose=OTPVerification.Purpose.REGISTRATION,
        verified_at__isnull=True,
    ).order_by("-created_at").first()


def register(request):
    if request.method == "POST":
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if settings.ACCOUNT_REQUIRE_OTP_VERIFICATION:
                try:
                    send_registration_otps(user)
                except Exception as exc:
                    messages.warning(request, f"Account created, but email OTP sending failed: {exc}")
                user.profile.mobile_verified = True
                user.profile.save(update_fields=["mobile_verified"])
            else:
                profile = user.profile
                profile.email_verified = True
                profile.mobile_verified = True
                profile.save(update_fields=["email_verified", "mobile_verified"])
            login(request, user, backend="accounts.backends.EmailOrMobileBackend")
            if settings.ACCOUNT_REQUIRE_OTP_VERIFICATION:
                messages.success(request, "Account created. Please verify your email OTP.")
                return redirect("verify_registration_otp")
            messages.success(request, "Account created. You can now submit your membership application.")
            return redirect("application_create")
    else:
        form = ApplicantRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def verify_registration_otp(request):
    profile = request.user.profile
    if not settings.ACCOUNT_REQUIRE_OTP_VERIFICATION:
        if not profile.email_verified or not profile.mobile_verified:
            profile.email_verified = True
            profile.mobile_verified = True
            profile.save(update_fields=["email_verified", "mobile_verified"])
        messages.success(request, "Account verified for testing. You can submit your membership application.")
        return redirect("application_create")

    if profile.email_verified:
        if not profile.mobile_verified:
            profile.mobile_verified = True
            profile.save(update_fields=["mobile_verified"])
        messages.success(request, "Your account is already verified.")
        return redirect("application_create")

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            email_otp = pending_otp(request.user, OTPVerification.Channel.EMAIL)
            email_ok = profile.email_verified or (email_otp and email_otp.verify(form.cleaned_data["email_otp"]))
            if email_ok:
                profile.email_verified = True
                profile.mobile_verified = True
                profile.save(update_fields=["email_verified", "mobile_verified"])
                messages.success(request, "Email OTP verified. You can now submit your membership application.")
                return redirect("application_create")
            messages.error(request, "Invalid or expired OTP. Please try again or resend OTP.")
    else:
        form = OTPVerificationForm()
    return render(request, "accounts/verify_otp.html", {"form": form})


@login_required
def resend_registration_otp(request):
    try:
        send_registration_otps(request.user)
        messages.success(request, "A new email OTP has been sent.")
    except Exception as exc:
        messages.error(request, f"Could not send email OTP: {exc}")
    return redirect("verify_registration_otp")
