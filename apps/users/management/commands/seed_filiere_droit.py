"""
Crée la filière Droit avec ses niveaux (L1, L2, L3, M1, M2).

Usage :
  python manage.py seed_filiere_droit
"""

from django.core.management.base import BaseCommand

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau


NIVEAUX_DROIT = ["L1", "L2", "L3", "M1", "M2"]


class Command(BaseCommand):
    help = "Crée la filière Droit et ses niveaux."

    def handle(self, *args, **options):
        filiere, created = Filiere.objects.get_or_create(name="Droit")
        status = "créée" if created else "existe déjà"
        self.stdout.write(f"Filière Droit — {status}")

        for code in NIVEAUX_DROIT:
            niveau, n_created = Niveau.objects.get_or_create(filiere=filiere, name=code)
            n_status = "créé" if n_created else "existe déjà"
            self.stdout.write(f"  └─ {code} — {n_status}")

        self.stdout.write(self.style.SUCCESS("\n✅  Filière Droit prête."))
