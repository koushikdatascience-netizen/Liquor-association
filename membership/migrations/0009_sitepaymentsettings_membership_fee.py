from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0008_sitepaymentsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitepaymentsettings",
            name="membership_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=5000.0,
                max_digits=10,
            ),
        ),
    ]