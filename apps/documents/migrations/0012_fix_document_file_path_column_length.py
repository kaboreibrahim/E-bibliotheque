from django.db import migrations, models

import apps.documents.utils


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0011_documentstorageconfiguration"),
    ]

    operations = [
        # TECH-005 : SQL brut (MySQL puis PostgreSQL) remplace par AlterField,
        # qui laisse Django generer le bon SQL pour le moteur reellement
        # configure (MySQL en prod cPanel, PostgreSQL en dev local). Cette
        # migration est deja marquee appliquee sur les bases existantes (elle
        # ne sera donc pas rejouee la) ; ce correctif ne joue que pour une
        # base neuve (manage.py test, nouvel environnement).
        migrations.AlterField(
            model_name='document',
            name='file_path',
            field=models.FileField(
                max_length=1024,
                upload_to=apps.documents.utils.document_upload_path,
                verbose_name='Fichier',
            ),
        ),
    ]
