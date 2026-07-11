import datetime
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("action", models.CharField(max_length=120)),
                ("target", models.CharField(max_length=160)),
                ("notes", models.TextField(blank=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="MembershipApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("SUBMITTED", "Application Submitted"),
                            ("APPROVED_PENDING_PAYMENT", "Approved - Pending Payment"),
                            ("ADDITIONAL_DOCUMENTS", "Additional Documents Requested"),
                            ("PAYMENT_SUBMITTED", "Payment Verification Pending"),
                            ("PAYMENT_APPROVED", "Payment Approved"),
                            ("MEMBER_ACTIVE", "Member Active"),
                            ("REJECTED", "Rejected"),
                            ("ON_HOLD", "On Hold"),
                        ],
                        default="DRAFT",
                        max_length=40,
                    ),
                ),
                ("remarks", models.TextField(blank=True)),
                ("full_name", models.CharField(max_length=160)),
                ("father_or_husband_name", models.CharField(max_length=160)),
                ("date_of_birth", models.DateField()),
                ("gender", models.CharField(choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")], max_length=10)),
                ("mobile_number", models.CharField(max_length=15)),
                ("email", models.EmailField(max_length=254)),
                ("residential_address", models.TextField()),
                ("office_address", models.TextField(blank=True)),
                ("shop_name", models.CharField(max_length=180)),
                ("trade_license_number", models.CharField(max_length=80)),
                ("excise_license_number", models.CharField(max_length=80)),
                ("excise_license_type", models.CharField(max_length=80)),
                ("gst_number", models.CharField(blank=True, max_length=30)),
                ("pan_number", models.CharField(max_length=20)),
                ("years_in_business", models.PositiveIntegerField(default=0)),
                ("district", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("passport_photo", models.ImageField(upload_to="kyc/photos/")),
                ("aadhaar_card", models.FileField(upload_to="kyc/aadhaar/")),
                ("pan_card", models.FileField(upload_to="kyc/pan/")),
                ("excise_license", models.FileField(upload_to="kyc/excise/")),
                ("trade_license", models.FileField(upload_to="kyc/trade/")),
                ("gst_certificate", models.FileField(blank=True, upload_to="kyc/gst/")),
                ("address_proof", models.FileField(upload_to="kyc/address/")),
                ("signature", models.ImageField(upload_to="kyc/signatures/")),
                ("declaration_accepted", models.BooleanField(default=False)),
                ("digital_signature", models.CharField(max_length=160)),
                ("applicant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=160)),
                ("message", models.TextField()),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="PaymentProof",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.DecimalField(decimal_places=2, default=5000.0, max_digits=10)),
                ("screenshot", models.FileField(upload_to="payments/screenshots/")),
                ("utr_number", models.CharField(max_length=80)),
                ("payment_date", models.DateField()),
                ("bank_name", models.CharField(max_length=120)),
                ("remarks", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending Verification"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("REUPLOAD_REQUESTED", "Re-upload Requested"),
                        ],
                        default="PENDING",
                        max_length=30,
                    ),
                ),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="payment", to="membership.membershipapplication")),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="verified_payments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Member",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("membership_number", models.CharField(max_length=40, unique=True)),
                ("membership_since", models.DateField()),
                ("category", models.CharField(default="Regular", max_length=80)),
                ("valid_till", models.DateField()),
                ("qr_code", models.ImageField(blank=True, upload_to="members/qr/")),
                ("is_active", models.BooleanField(default=True)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="member", to="membership.membershipapplication")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="member_record", to=settings.AUTH_USER_MODEL)),
            ],
            options={"abstract": False},
        ),
    ]
