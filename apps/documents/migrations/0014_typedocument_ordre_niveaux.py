from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0013_remove_document_encadreur'),
        ('niveau', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='typedocument',
            name='ordre',
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage"),
        ),
        migrations.AddField(
            model_name='typedocument',
            name='niveaux',
            field=models.ManyToManyField(
                blank=True,
                related_name='types_documents',
                to='niveau.niveau',
                verbose_name='Niveaux associés',
            ),
        ),
        migrations.AlterModelOptions(
            name='typedocument',
            options={
                'ordering': ['ordre', 'name'],
                'verbose_name': 'Type de document',
                'verbose_name_plural': 'Types de documents',
            },
        ),
    ]
