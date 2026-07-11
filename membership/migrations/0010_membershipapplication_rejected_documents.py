from django.db import migrations
from django.db.models import JSONField


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0009_sitepaymentsettings_membership_fee"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershipapplication",
            name="rejected_documents",
            field=JSONField(
                blank=True,
                default=list,
                help_text="List of document field keys rejected by admin (e.g. ['excise_license']).",
            ),
        ),
    ]