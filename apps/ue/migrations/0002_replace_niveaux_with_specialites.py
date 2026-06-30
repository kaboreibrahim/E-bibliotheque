from django.db import migrations, models


def copy_niveaux_to_specialites(apps, schema_editor):
    UE = apps.get_model("ue", "UE")
    Specialite = apps.get_model("specialites", "Specialite")

    for ue in UE.objects.prefetch_related("niveaux").all():
        niveau_ids = list(ue.niveaux.values_list("id", flat=True))
        if not niveau_ids:
            continue

        specialite_ids = list(
            Specialite.objects.filter(niveau_id__in=niveau_ids).values_list("id", flat=True)
        )
        if specialite_ids:
            ue.specialites.set(specialite_ids)


def copy_specialites_to_niveaux(apps, schema_editor):
    UE = apps.get_model("ue", "UE")

    for ue in UE.objects.prefetch_related("specialites").all():
        niveau_ids = list(
            ue.specialites.values_list("niveau_id", flat=True).distinct()
        )
        if niveau_ids:
            ue.niveaux.set(niveau_ids)


class Migration(migrations.Migration):

    dependencies = [
        ("specialites", "0002_alter_specialite_niveau"),
        ("ue", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ue",
            name="specialites",
            field=models.ManyToManyField(
                blank=True,
                related_name="ues",
                to="specialites.specialite",
                verbose_name="Specialites concernees",
            ),
        ),
        migrations.RunPython(copy_niveaux_to_specialites, copy_specialites_to_niveaux),
        migrations.RemoveField(
            model_name="ue",
            name="niveaux",
        ),
    ]
