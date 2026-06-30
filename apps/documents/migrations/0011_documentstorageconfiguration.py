from django.db import migrations, models


def create_storage_configuration(apps, schema_editor):
    document_storage_configuration = apps.get_model(
        "documents",
        "DocumentStorageConfiguration",
    )
    document_storage_configuration.objects.get_or_create(
        pk=1,
        defaults={"server_disk_capacity_mb": 0},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0010_alter_document_file_path_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentStorageConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "server_disk_capacity_mb",
                    models.PositiveBigIntegerField(
                        default=0,
                        help_text=(
                            "Capacite totale du disque dedie au stockage des documents, en Mo."
                        ),
                        verbose_name="Capacite disque du serveur (Mo)",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Cree le",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Modifie le",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuration de stockage document",
                "verbose_name_plural": "Configuration de stockage document",
            },
        ),
        migrations.RunPython(
            create_storage_configuration,
            migrations.RunPython.noop,
        ),
    ]
