"""
PERF-001 : renseigne file_size pour les documents deja existants, crees
avant l'ajout du champ. Les nouveaux documents le calculent automatiquement
dans Document.clean() a chaque sauvegarde.
"""
from django.db import migrations


def backfill_file_size(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')
    documents = Document.objects.filter(file_size__isnull=True).exclude(file_path='')

    for document in documents.iterator():
        try:
            size = document.file_path.size
        except (FileNotFoundError, OSError, ValueError):
            continue
        Document.objects.filter(pk=document.pk).update(file_size=size)


def noop_reverse(apps, schema_editor):
    """Rien a annuler : on ne fait que renseigner des valeurs manquantes."""


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0016_document_file_size'),
    ]

    operations = [
        migrations.RunPython(backfill_file_size, noop_reverse),
    ]
