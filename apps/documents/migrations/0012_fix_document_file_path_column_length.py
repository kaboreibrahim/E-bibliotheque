from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0011_documentstorageconfiguration"),
    ]

    operations = [
        migrations.RunSQL(
            # TECH-005 : syntaxe MySQL (MODIFY COLUMN) remplacee par la syntaxe
            # PostgreSQL (moteur reellement configure). Cette migration est deja
            # marquee appliquee sur les bases existantes (elle ne sera donc pas
            # rejouee la) ; ce correctif ne joue que pour une base neuve
            # (manage.py test, nouvel environnement, future prod).
            sql=(
                "ALTER TABLE documents_document "
                "ALTER COLUMN file_path TYPE varchar(1024);"
            ),
            reverse_sql=(
                "ALTER TABLE documents_document "
                "ALTER COLUMN file_path TYPE varchar(100);"
            ),
        ),
    ]
