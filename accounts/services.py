import json
import random
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import OTPVerification


def generate_otp():
    start = 10 ** (settings.OTP_LENGTH - 1)
    end = (10**settings.OTP_LENGTH) - 1
    return str(random.randint(start, end))


def send_registration_otps(user):
    profile = user.profile
    expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    email_code = generate_otp()
    OTPVerification.create_code(
        user=user,
        channel=OTPVerification.Channel.EMAIL,
        destination=user.email,
        code=email_code,
        expires_at=expires_at,
    )
    send_email_otp(user.email, email_code)

    mobile_code = generate_otp()
    OTPVerification.create_code(
        user=user,
        channel=OTPVerification.Channel.WHATSAPP,
        destination=profile.mobile_number,
        code=mobile_code,
        expires_at=expires_at,
    )
    send_whatsapp_otp(profile.mobile_number, mobile_code, fallback_email=user.email)


def send_email_otp(email, code):
    if not email:
        return
    send_mail(
        subject="Your membership portal email OTP",
        message=f"Your email verification OTP is {code}. It expires in {settings.OTP_EXPIRY_MINUTES} minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def send_whatsapp_otp(mobile_number, code, fallback_email=None):
    if not settings.WHATSAPP_OTP_ENABLED:
        if settings.DEBUG and fallback_email:
            send_mail(
                subject="Development mobile/WhatsApp OTP fallback",
                message=f"WhatsApp provider is disabled. Mobile OTP for {mobile_number}: {code}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[fallback_email],
                fail_silently=True,
            )
        return False
    if not settings.WHATSAPP_OTP_API_URL or not settings.WHATSAPP_OTP_TOKEN:
        return False

    payload = {
        "to": mobile_number,
        "from": settings.WHATSAPP_OTP_FROM,
        "message": f"Your membership portal mobile OTP is {code}. It expires in {settings.OTP_EXPIRY_MINUTES} minutes.",
    }
    request = urllib.request.Request(
        settings.WHATSAPP_OTP_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.WHATSAPP_OTP_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError):
        return False
