import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OTPVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "channel",
                    models.CharField(
                        choices=[("EMAIL", "Email"), ("WHATSAPP", "WhatsApp"), ("MOBILE", "Mobile")],
                        max_length=20,
                    ),
                ),
                (
                    "purpose",
                    models.CharField(
                        choices=[("REGISTRATION", "Registration"), ("LOGIN", "Login")],
                        default="REGISTRATION",
                        max_length=30,
                    ),
                ),
                ("destination", models.CharField(max_length=254)),
                ("code_hash", models.CharField(max_length=256)),
                ("expires_at", models.DateTimeField()),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="otp_codes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
