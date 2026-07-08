from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0004_email_whatsapp_broadcast_channel"),
    ]

    operations = [
        migrations.AddField(
            model_name="broadcastmessage",
            name="recipient_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
