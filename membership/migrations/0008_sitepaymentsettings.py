from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0007_align_membership_application_reference_form"),
    ]

    operations = [
        migrations.CreateModel(
            name="SitePaymentSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account_name", models.CharField(blank=True, max_length=160)),
                ("bank_name", models.CharField(blank=True, max_length=160)),
                ("account_number", models.CharField(blank=True, max_length=80)),
                ("ifsc", models.CharField(blank=True, max_length=40)),
                ("upi_id", models.CharField(blank=True, max_length=120)),
                ("qr_code", models.ImageField(blank=True, upload_to="payments/qr/")),
            ],
            options={
                "verbose_name": "payment setting",
                "verbose_name_plural": "payment settings",
            },
        ),
    ]
