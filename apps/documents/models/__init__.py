from apps.documents.models.document import Document
from apps.documents.models.document_type_models import TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.ue.models import ECUE, UE

__all__ = [
    "Document",
    "TypeDocument",
    "Filiere",
    "Niveau",
    "UE",
    "ECUE",
]
