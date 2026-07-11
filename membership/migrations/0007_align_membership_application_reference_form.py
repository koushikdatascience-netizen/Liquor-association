from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0006_broadcastmessage_recipient_mobile"),
    ]

    operations = [
        migrations.AddField("membershipapplication", "age", models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField("membershipapplication", "alternate_delegate_address", models.TextField(blank=True)),
        migrations.AddField("membershipapplication", "alternate_delegate_name", models.CharField(blank=True, max_length=160)),
        migrations.AddField("membershipapplication", "alternate_delegate_photo", models.ImageField(blank=True, upload_to="kyc/delegates/alternate/")),
        migrations.AddField("membershipapplication", "alternate_delegate_role", models.CharField(blank=True, max_length=120)),
        migrations.AddField("membershipapplication", "entity_type", models.CharField(blank=True, max_length=80)),
        migrations.AddField("membershipapplication", "licence_category", models.CharField(blank=True, max_length=40)),
        migrations.AddField("membershipapplication", "nationality", models.CharField(default="Indian", max_length=80)),
        migrations.AddField("membershipapplication", "office_phone", models.CharField(blank=True, max_length=20)),
        migrations.AddField("membershipapplication", "partner_md_names", models.TextField(blank=True)),
        migrations.AddField("membershipapplication", "partnership_deed", models.FileField(blank=True, upload_to="kyc/deed/")),
        migrations.AddField("membershipapplication", "pin_code", models.CharField(blank=True, max_length=6)),
        migrations.AddField("membershipapplication", "primary_delegate_address", models.TextField(blank=True)),
        migrations.AddField("membershipapplication", "primary_delegate_designation", models.CharField(blank=True, max_length=120)),
        migrations.AddField("membershipapplication", "primary_delegate_name", models.CharField(blank=True, max_length=160)),
        migrations.AddField("membershipapplication", "primary_delegate_photo", models.ImageField(blank=True, upload_to="kyc/delegates/primary/")),
        migrations.AddField("membershipapplication", "residence_phone", models.CharField(blank=True, max_length=20)),
        migrations.AddField("membershipapplication", "shop_phone", models.CharField(blank=True, max_length=20)),
        migrations.AddField("membershipapplication", "style_name", models.CharField(blank=True, max_length=180)),
        migrations.AddField("membershipapplication", "whatsapp_number", models.CharField(blank=True, max_length=15)),
        migrations.AlterField("membershipapplication", "aadhaar_card", models.FileField(blank=True, upload_to="kyc/aadhaar/")),
        migrations.AlterField("membershipapplication", "address_proof", models.FileField(blank=True, upload_to="kyc/address/")),
        migrations.AlterField("membershipapplication", "date_of_birth", models.DateField(blank=True, null=True)),
        migrations.AlterField("membershipapplication", "excise_license", models.FileField(blank=True, upload_to="kyc/excise/")),
        migrations.AlterField("membershipapplication", "father_or_husband_name", models.CharField(blank=True, max_length=160)),
        migrations.AlterField("membershipapplication", "pan_card", models.FileField(blank=True, upload_to="kyc/pan/")),
        migrations.AlterField("membershipapplication", "pan_number", models.CharField(blank=True, max_length=20)),
        migrations.AlterField("membershipapplication", "passport_photo", models.ImageField(blank=True, upload_to="kyc/photos/")),
        migrations.AlterField("membershipapplication", "signature", models.ImageField(blank=True, upload_to="kyc/signatures/")),
        migrations.AlterField("membershipapplication", "state", models.CharField(blank=True, default="West Bengal", max_length=100)),
        migrations.AlterField("membershipapplication", "trade_license", models.FileField(blank=True, upload_to="kyc/trade/")),
        migrations.AlterField("membershipapplication", "trade_license_number", models.CharField(blank=True, max_length=80)),
    ]
