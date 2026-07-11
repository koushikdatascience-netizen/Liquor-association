from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import OTPVerification


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    WHATSAPP_NOTIFICATIONS_ENABLED=False,
)
class OtpAuthenticationTests(TestCase):
    def test_registration_creates_passwordless_user_and_sends_otp(self):
        response = self.client.post(
            reverse("register"),
            {"email": "member@example.com", "mobile_number": "9876543210"},
        )

        self.assertRedirects(response, reverse("verify_registration_otp"))
        user = User.objects.get(email="member@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.mobile_number, "9876543210")
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            OTPVerification.objects.filter(
                user=user,
                purpose=OTPVerification.Purpose.REGISTRATION,
                channel=OTPVerification.Channel.EMAIL,
            ).exists()
        )

    def test_member_login_requests_otp_without_password(self):
        user = User.objects.create_user(username="member@example.com", email="member@example.com")
        user.set_unusable_password()
        user.save(update_fields=["password"])
        user.profile.mobile_number = "9876543210"
        user.profile.save(update_fields=["mobile_number"])

        response = self.client.post(reverse("login"), {"identifier": "member@example.com"})

        self.assertRedirects(response, reverse("login_verify_otp"))
        self.assertEqual(self.client.session["login_otp_user_id"], user.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            OTPVerification.objects.filter(
                user=user,
                purpose=OTPVerification.Purpose.LOGIN,
                channel=OTPVerification.Channel.EMAIL,
            ).exists()
        )

    @patch("accounts.services.send_login_otps")
    def test_admin_cannot_use_member_otp_login(self, send_login_otps):
        admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
        )

        response = self.client.post(reverse("login"), {"identifier": admin.email})

        self.assertRedirects(response, reverse("admin_login"))
        send_login_otps.assert_not_called()
