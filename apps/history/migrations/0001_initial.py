from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoriqueAction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("CONNEXION_ETAPE_1", "Connexion etape 1"),
                            ("CONNEXION", "Connexion"),
                            ("DECONNEXION", "Deconnexion"),
                            ("CONNEXION_ECHEC", "Connexion echouee"),
                            ("OTP_ENVOI", "OTP envoye"),
                            ("OTP_ECHEC", "OTP echoue"),
                            ("TOTP_ACTIVE", "TOTP valide"),
                            ("TOTP_ECHEC", "TOTP echoue"),
                            ("DOCUMENT_AJOUT", "Document ajoute"),
                            ("DOCUMENT_MODIFICATION", "Document modifie"),
                            ("DOCUMENT_SUPPRESSION", "Document supprime"),
                            ("UTILISATEUR_CREATION", "Utilisateur cree"),
                            ("UTILISATEUR_MODIF", "Utilisateur modifie"),
                            ("UTILISATEUR_DESACTIVE", "Utilisateur desactive"),
                            ("UTILISATEUR_SUPPRIME", "Utilisateur supprime"),
                            ("FAVORI_AJOUT", "Favori ajoute"),
                            ("FAVORI_SUPPRESSION", "Favori supprime"),
                            ("CONSULTATION_VUE", "Consultation document"),
                            ("CONSULTATION_RECHERCHE", "Recherche effectuee"),
                            ("CONSULTATION_TERMINEE", "Consultation terminee"),
                        ],
                        db_index=True,
                        max_length=50,
                        verbose_name="Action",
                    ),
                ),
                ("user_email", models.EmailField(blank=True, max_length=254, verbose_name="Email utilisateur")),
                ("user_type", models.CharField(blank=True, max_length=20, verbose_name="Type utilisateur")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="Details")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="Adresse IP")),
                ("user_agent", models.CharField(blank=True, max_length=500, verbose_name="User agent")),
                (
                    "statut",
                    models.CharField(
                        choices=[("succes", "Succes"), ("echec", "Echec")],
                        db_index=True,
                        default="succes",
                        max_length=10,
                        verbose_name="Statut",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Cree le")),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="historique_actions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Utilisateur",
                    ),
                ),
            ],
            options={
                "verbose_name": "Historique d'action",
                "verbose_name_plural": "Historiques d'actions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="historiqueaction",
            index=models.Index(fields=["action", "-created_at"], name="history_his_action_c1b3c9_idx"),
        ),
        migrations.AddIndex(
            model_name="historiqueaction",
            index=models.Index(fields=["statut", "-created_at"], name="history_his_statut_ea592a_idx"),
        ),
        migrations.AddIndex(
            model_name="historiqueaction",
            index=models.Index(fields=["user", "-created_at"], name="history_his_user_id_89d8ec_idx"),
        ),
    ]
