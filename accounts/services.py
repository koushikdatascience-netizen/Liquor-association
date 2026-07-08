import random
from datetime import timedelta

from django.conf import settings
from django.core.mail import BadHeaderError
from django.core.mail import send_mail
from django.utils import timezone

from .models import OTPVerification


def generate_otp():
    start = 10 ** (settings.OTP_LENGTH - 1)
    end = (10**settings.OTP_LENGTH) - 1
    return str(random.randint(start, end))


def send_registration_otps(user):
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


def send_email_otp(email, code):
    if not email:
        return
    try:
        send_mail(
            subject="Your membership portal email OTP",
            message=f"Your email verification OTP is {code}. It expires in {settings.OTP_EXPIRY_MINUTES} minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except (OSError, TimeoutError, BadHeaderError):
        raise RuntimeError("Email service did not respond. Please try resending the OTP in a minute.")
