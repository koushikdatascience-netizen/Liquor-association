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

        self.assertRedirects(response, reverse("member_dashboard"))
        user = User.objects.get(email="member@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.mobile_number, "9876543210")
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertEqual(self.client.session["registration_otp_user_id"], user.pk)
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

        response = self.client.post(
            reverse("login"),
            {"email": "member@example.com", "mobile_number": "9876543210"},
        )

        self.assertRedirects(response, reverse("login_verify_otp"))
        self.assertEqual(self.client.session["auth_otp_user_id"], user.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            OTPVerification.objects.filter(
                user=user,
                purpose=OTPVerification.Purpose.LOGIN,
                channel=OTPVerification.Channel.EMAIL,
            ).exists()
        )

    @override_settings(WHATSAPP_NOTIFICATIONS_ENABLED=True)
    @patch("accounts.services.send_whatsapp_otp", return_value=True)
    @patch("accounts.services.send_email_otp", side_effect=RuntimeError("SMTP failed"))
    def test_login_continues_to_otp_when_email_fails_but_whatsapp_sends(self, _send_email, _send_whatsapp):
        user = User.objects.create_user(username="member2@example.com", email="member2@example.com")
        user.set_unusable_password()
        user.save(update_fields=["password"])
        user.profile.mobile_number = "9876543211"
        user.profile.save(update_fields=["mobile_number"])

        response = self.client.post(
            reverse("login"),
            {"email": "member2@example.com", "mobile_number": "9876543211"},
            follow=True,
        )

        self.assertRedirects(response, reverse("login_verify_otp"))
        self.assertEqual(self.client.session["auth_otp_user_id"], user.pk)
        self.assertContains(response, "Email delivery failed")
        self.assertTrue(
            OTPVerification.objects.filter(
                user=user,
                purpose=OTPVerification.Purpose.LOGIN,
                channel=OTPVerification.Channel.WHATSAPP,
            ).exists()
        )

    @override_settings(WHATSAPP_NOTIFICATIONS_ENABLED=True)
    @patch("accounts.services.send_whatsapp_otp", return_value=False)
    @patch("accounts.services.send_email_otp", side_effect=RuntimeError("SMTP failed"))
    def test_login_blocks_when_email_and_whatsapp_both_fail(self, _send_email, _send_whatsapp):
        user = User.objects.create_user(username="member3@example.com", email="member3@example.com")
        user.set_unusable_password()
        user.save(update_fields=["password"])
        user.profile.mobile_number = "9876543212"
        user.profile.save(update_fields=["mobile_number"])

        response = self.client.post(
            reverse("login"),
            {"email": "member3@example.com", "mobile_number": "9876543212"},
            follow=True,
        )

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("auth_otp_user_id", self.client.session)
        self.assertContains(response, "Could not send OTP by email or WhatsApp")

    @patch("accounts.services.send_login_otps")
    def test_admin_cannot_use_member_otp_login(self, send_login_otps):
        admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
        )

        response = self.client.post(reverse("login"), {"email": admin.email, "mobile_number": "9876543210"})

        self.assertRedirects(response, reverse("admin_login"))
        send_login_otps.assert_not_called()

    def test_custom_admin_pages_redirect_to_admin_login(self):
        response = self.client.get(reverse("staff_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("admin_login")))
        self.assertIn("next=/admin/dashboard/", response["Location"])

    def test_django_admin_url_redirects_to_custom_admin(self):
        response = self.client.get("/django-admin/")

        self.assertRedirects(response, reverse("staff_dashboard"), fetch_redirect_response=False)
