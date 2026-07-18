from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0011_membershipapplication_documents_reuploaded_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershipapplication",
            name="other_association_declaration_accepted",
            field=models.BooleanField(default=False),
        ),
    ]
