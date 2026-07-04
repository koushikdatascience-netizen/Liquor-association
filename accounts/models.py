from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


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


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
