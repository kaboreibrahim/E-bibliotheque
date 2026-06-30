from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0006_document_base64_storage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="type",
            field=models.CharField(max_length=100, verbose_name="Type de document"),
        ),
    ]
