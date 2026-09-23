"""
TECH-005 : corrige la migration 0012, ecrite en syntaxe MySQL
(MODIFY COLUMN), qui echoue sur PostgreSQL (moteur reellement configure).
Sans cette migration, `manage.py test` et tout `migrate` sur une base
PostgreSQL neuve echouent avant meme de commencer.

On n'edite pas la migration 0012 elle-meme (deja marquee appliquee sur la
base de dev existante) : on ajoute un correctif en aval, idempotent.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0017_backfill_document_file_size'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE documents_document ALTER COLUMN file_path TYPE varchar(1024);",
            reverse_sql="ALTER TABLE documents_document ALTER COLUMN file_path TYPE varchar(100);",
        ),
    ]
