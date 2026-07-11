import random
import logging
import smtplib
from datetime import timedelta

from django.conf import settings
from django.core.mail import BadHeaderError
from django.core.mail import send_mail
from django.utils import timezone

from config.pinbot import send_template_message
from .models import OTPVerification


logger = logging.getLogger(__name__)


def generate_otp():
    start = 10 ** (settings.OTP_LENGTH - 1)
    end = (10**settings.OTP_LENGTH) - 1
    return str(random.randint(start, end))


def send_account_otps(user, purpose):
    expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    code = generate_otp()
    label = "login" if purpose == OTPVerification.Purpose.LOGIN else "registration"
    errors = []

    if user.email:
        OTPVerification.create_code(
            user=user,
            channel=OTPVerification.Channel.EMAIL,
            destination=user.email,
            code=code,
            expires_at=expires_at,
            purpose=purpose,
        )
        try:
            send_email_otp(user.email, code, label)
        except RuntimeError as exc:
            errors.append(str(exc))

    mobile_number = getattr(getattr(user, "profile", None), "mobile_number", "")
    if mobile_number:
        OTPVerification.create_code(
            user=user,
            channel=OTPVerification.Channel.WHATSAPP,
            destination=mobile_number,
            code=code,
            expires_at=expires_at,
            purpose=purpose,
        )
        send_whatsapp_otp(mobile_number, code, label)

    if errors:
        raise RuntimeError(" ".join(errors))


def send_registration_otps(user):
    send_account_otps(user, OTPVerification.Purpose.REGISTRATION)


def send_login_otps(user):
    send_account_otps(user, OTPVerification.Purpose.LOGIN)


def send_email_otp(email, code, purpose_label):
    if not email:
        return
    try:
        send_mail(
            subject=f"Your membership portal {purpose_label} OTP",
            message=f"Your {purpose_label} OTP is {code}. It expires in {settings.OTP_EXPIRY_MINUTES} minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except (OSError, TimeoutError, BadHeaderError, smtplib.SMTPException) as exc:
        logger.warning("OTP email failed for %s: %s", email, exc)
        raise RuntimeError("Email service did not respond. Please try resending the OTP in a minute.")


def send_whatsapp_otp(mobile_number, code, purpose_label):
    if not mobile_number or not settings.WHATSAPP_NOTIFICATIONS_ENABLED:
        return False
    message = f"Your {purpose_label} OTP is {code}. It expires in {settings.OTP_EXPIRY_MINUTES} minutes."
    return send_template_message(
        mobile_number,
        settings.PINBOT_NOTIFICATION_TEMPLATE_NAME,
        [settings.ASSOCIATION_NAME, f"{purpose_label.title()} OTP", message],
    )
