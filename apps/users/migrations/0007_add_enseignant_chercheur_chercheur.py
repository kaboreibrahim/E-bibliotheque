import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import safedelete.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_etudiant_options_etudiant_activation_suspendue_and_more'),
    ]

    operations = [
        # Agrandir le champ user_type pour accueillir ENSEIGNANT_CHERCHEUR (20 chars)
        migrations.AlterField(
            model_name='user',
            name='user_type',
            field=models.CharField(
                choices=[
                    ('ETUDIANT', 'Étudiant'),
                    ('PERSONNE_EXTERNE', 'Personne externe'),
                    ('BIBLIOTHECAIRE', 'Bibliothécaire'),
                    ('ADMINISTRATEUR', 'Administrateur'),
                    ('ENSEIGNANT_CHERCHEUR', 'Enseignant-Chercheur'),
                    ('CHERCHEUR', 'Chercheur'),
                ],
                default='ETUDIANT',
                max_length=25,
                verbose_name="Type d'utilisateur",
            ),
        ),

        # Table EnseignantChercheur
        migrations.CreateModel(
            name='EnseignantChercheur',
            fields=[
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('numero_piece', models.CharField(blank=True, max_length=100, verbose_name="Numero de piece d'identite")),
                ('lieu_habitation', models.CharField(blank=True, max_length=255, verbose_name="Lieu d'habitation")),
                ('annee_service', models.PositiveIntegerField(blank=True, help_text="Annee d'entree en service a l'universite.", null=True, verbose_name='Annee de service')),
                ('specialite_enseignee', models.CharField(blank=True, max_length=255, verbose_name='Specialite enseignee / domaine de recherche')),
                ('activation_suspendue', models.BooleanField(default=False, help_text='Indique si le compte a ete suspendu par un administrateur.', verbose_name='Compte suspendu')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Cree le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Modifie le')),
                ('user', models.OneToOneField(
                    limit_choices_to={'user_type': 'ENSEIGNANT_CHERCHEUR'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profil_enseignant_chercheur',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Compte utilisateur',
                )),
            ],
            options={
                'verbose_name': 'Enseignant-Chercheur',
                'verbose_name_plural': 'Enseignants-Chercheurs',
                'ordering': ['user__last_name', 'user__first_name'],
            },
            bases=(safedelete.models.SafeDeleteModel, models.Model),
        ),

        # Table Chercheur
        migrations.CreateModel(
            name='Chercheur',
            fields=[
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('numero_piece', models.CharField(blank=True, max_length=100, verbose_name="Numero de piece d'identite")),
                ('lieu_habitation', models.CharField(blank=True, max_length=255, verbose_name="Lieu d'habitation")),
                ('annee_service', models.PositiveIntegerField(blank=True, help_text="Annee d'entree en service a l'universite.", null=True, verbose_name='Annee de service')),
                ('specialite_enseignee', models.CharField(blank=True, max_length=255, verbose_name='Specialite enseignee / domaine de recherche')),
                ('activation_suspendue', models.BooleanField(default=False, help_text='Indique si le compte a ete suspendu par un administrateur.', verbose_name='Compte suspendu')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Cree le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Modifie le')),
                ('user', models.OneToOneField(
                    limit_choices_to={'user_type': 'CHERCHEUR'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profil_chercheur',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Compte utilisateur',
                )),
            ],
            options={
                'verbose_name': 'Chercheur',
                'verbose_name_plural': 'Chercheurs',
                'ordering': ['user__last_name', 'user__first_name'],
            },
            bases=(safedelete.models.SafeDeleteModel, models.Model),
        ),
    ]
