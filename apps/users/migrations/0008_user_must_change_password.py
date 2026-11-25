from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_add_enseignant_chercheur_chercheur'),
    ]

    operations = [
        # Les comptes existants restent à False : seuls les nouveaux comptes
        # devront remplacer leur mot de passe temporaire.
        migrations.AddField(
            model_name='user',
            name='must_change_password',
            field=models.BooleanField(
                default=False,
                help_text="Vrai tant que le mot de passe temporaire reçu par email n'a pas été remplacé.",
                verbose_name='Changement de mot de passe requis',
            ),
        ),
    ]
