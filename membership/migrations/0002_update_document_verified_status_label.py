from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("membership", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="membershipapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"),
                    ("SUBMITTED", "Application Submitted"),
                    ("APPROVED_PENDING_PAYMENT", "Documents Verified - Pending Payment"),
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
    ]
