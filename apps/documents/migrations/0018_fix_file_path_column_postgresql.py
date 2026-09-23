"""
TECH-005 (correctif) : la premiere version de cette migration utilisait du
SQL brut PostgreSQL (ALTER COLUMN ... TYPE), qui plante sur MySQL/MariaDB
(erreur 1064 constatee en production cPanel : le projet tourne bien sur
MySQL en prod, PostgreSQL seulement en dev local — voir aussi la migration
0012, corrigee de la meme facon).

migrations.AlterField laisse Django generer le bon SQL pour le moteur
reellement configure (MODIFY COLUMN sur MySQL, ALTER COLUMN ... TYPE sur
PostgreSQL) au lieu de coder une syntaxe SQL brute propre a un seul moteur.
"""
from django.db import migrations, models

import apps.documents.utils


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0017_backfill_document_file_size'),
    ]

    operations = [
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
