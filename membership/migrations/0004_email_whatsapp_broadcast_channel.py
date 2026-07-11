from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0003_notification_channel_broadcastmessage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="broadcastmessage",
            name="channel",
            field=models.CharField(
                choices=[
                    ("IN_APP", "In-app"),
                    ("EMAIL", "Email"),
                    ("WHATSAPP", "WhatsApp"),
                    ("EMAIL_WHATSAPP", "Email + WhatsApp"),
                ],
                default="IN_APP",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="channel",
            field=models.CharField(
                choices=[
                    ("IN_APP", "In-app"),
                    ("EMAIL", "Email"),
                    ("WHATSAPP", "WhatsApp"),
                    ("EMAIL_WHATSAPP", "Email + WhatsApp"),
                ],
                default="IN_APP",
                max_length=20,
            ),
        ),
    ]
