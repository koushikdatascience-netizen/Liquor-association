from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mobile_number", models.CharField(blank=True, max_length=15)),
                ("mobile_verified", models.BooleanField(default=False)),
                ("email_verified", models.BooleanField(default=False)),
                (
                    "role",
                    models.CharField(
                        choices=[("APPLICANT", "Applicant"), ("MEMBER", "Member"), ("ADMIN", "Admin")],
                        default="APPLICANT",
                        max_length=20,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
