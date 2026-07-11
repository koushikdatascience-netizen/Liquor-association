from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0005_broadcastmessage_recipient_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="broadcastmessage",
            name="recipient_mobile",
            field=models.CharField(blank=True, max_length=15),
        ),
    ]
