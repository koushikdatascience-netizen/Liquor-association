from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
import os


class Command(BaseCommand):
    help = "Create or update the production admin user from environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_ADMIN_USERNAME", "admin").strip()
        email = os.environ.get("DJANGO_ADMIN_EMAIL", "admin@example.com").strip()
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "").strip()

        if not password:
            self.stdout.write("DJANGO_ADMIN_PASSWORD is not set. Skipping admin bootstrap.")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin user: {username}"))
