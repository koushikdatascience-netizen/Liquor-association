import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("membership", "0002_update_document_verified_status_label"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="channel",
            field=models.CharField(
                choices=[("IN_APP", "In-app"), ("EMAIL", "Email"), ("WHATSAPP", "WhatsApp")],
                default="IN_APP",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="BroadcastMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=160)),
                ("message", models.TextField()),
                (
                    "audience",
                    models.CharField(
                        choices=[
                            ("ALL_MEMBERS", "All Members"),
                            ("DISTRICT", "District-wise"),
                            ("INDIVIDUAL", "Individual Member"),
                            ("PENDING_APPLICANTS", "Pending Applicants"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[("IN_APP", "In-app"), ("EMAIL", "Email"), ("WHATSAPP", "WhatsApp")],
                        default="IN_APP",
                        max_length=20,
                    ),
                ),
                ("district", models.CharField(blank=True, max_length=100)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("sent_count", models.PositiveIntegerField(default=0)),
                (
                    "recipient",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "sent_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_broadcasts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
