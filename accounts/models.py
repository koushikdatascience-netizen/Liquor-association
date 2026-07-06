from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Profile(models.Model):
    class Role(models.TextChoices):
        APPLICANT = "APPLICANT", "Applicant"
        MEMBER = "MEMBER", "Member"
        ADMIN = "ADMIN", "Admin"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    mobile_number = models.CharField(max_length=15, blank=True)
    mobile_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.APPLICANT)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class OTPVerification(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = "REGISTRATION", "Registration"
        LOGIN = "LOGIN", "Login"

    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        MOBILE = "MOBILE", "Mobile"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    purpose = models.CharField(max_length=30, choices=Purpose.choices, default=Purpose.REGISTRATION)
    destination = models.CharField(max_length=254)
    code_hash = models.CharField(max_length=256)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_code(cls, user, channel, destination, code, expires_at, purpose=Purpose.REGISTRATION):
        cls.objects.filter(user=user, channel=channel, purpose=purpose, verified_at__isnull=True).delete()
        return cls.objects.create(
            user=user,
            channel=channel,
            purpose=purpose,
            destination=destination,
            code_hash=make_password(code),
            expires_at=expires_at,
        )

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def verify(self, code):
        self.attempts += 1
        if self.is_expired or not check_password(code, self.code_hash):
            self.save(update_fields=["attempts"])
            return False
        self.verified_at = timezone.now()
        self.save(update_fields=["attempts", "verified_at"])
        return True

    def __str__(self):
        return f"{self.user} - {self.channel} - {self.purpose}"


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
