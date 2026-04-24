from datetime import datetime, timezone as dt_timezone
from io import BytesIO
import re
from zipfile import ZIP_DEFLATED, ZipFile

from django.utils import timezone


_INVALID_XML_RE = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F]"
)
_INVALID_SHEET_NAME_RE = re.compile(r"[:\\/?*\[\]]")


def _sanitize_text(value) -> str:
    if value is None:
        return ""
    return _INVALID_XML_RE.sub("", str(value))


def _escape_xml(value) -> str:
    text = _sanitize_text(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _column_name(index: int) -> str:
    letters: list[str] = []
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def _sheet_name(value: str) -> str:
    cleaned = _INVALID_SHEET_NAME_RE.sub("-", value or "Feuille1").strip()
    return (cleaned or "Feuille1")[:31]


def _build_sheet_xml(headers: list[str], rows: list[list[str]]) -> str:
    xml_rows: list[str] = []
    all_rows = [headers] + rows

    for row_index, row_values in enumerate(all_rows, start=1):
        cells: list[str] = []
        for col_index, value in enumerate(row_values, start=1):
            ref = f"{_column_name(col_index)}{row_index}"
            text = _escape_xml(value)
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'
            )
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        f'{"".join(xml_rows)}'
        "</sheetData>"
        "</worksheet>"
    )


def build_simple_xlsx(sheet_name: str, headers: list[str], rows: list[list[str]]) -> bytes:
    safe_sheet_name = _sheet_name(sheet_name)
    timestamp = datetime.now(dt_timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""
    workbook = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{_escape_xml(safe_sheet_name)}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""
    app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>E-BIBLIO</Application>
</Properties>
"""
    core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/"
                   xmlns:dcmitype="http://purl.org/dc/dcmitype/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>E-BIBLIO</dc:creator>
  <cp:lastModifiedBy>E-BIBLIO</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>
"""

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
        zip_file.writestr("[Content_Types].xml", content_types)
        zip_file.writestr("_rels/.rels", root_rels)
        zip_file.writestr("xl/workbook.xml", workbook)
        zip_file.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zip_file.writestr("xl/worksheets/sheet1.xml", _build_sheet_xml(headers, rows))
        zip_file.writestr("docProps/app.xml", app_xml)
        zip_file.writestr("docProps/core.xml", core_xml)
    return buffer.getvalue()


class EtudiantExcelExportService:
    HEADERS = [
        "Type profil",
        "Profil ID",
        "User ID",
        "Matricule",
        "Prenom",
        "Nom",
        "Nom complet",
        "Email",
        "Telephone",
        "Date de naissance",
        "Type utilisateur",
        "Compte actif",
        "2FA active",
        "Derniere verification TOTP",
        "Derniere connexion",
        "Avatar",
        "Filiere ID",
        "Filiere",
        "Niveau ID",
        "Niveau",
        "Specialite ID",
        "Specialite",
        "Annee inscription",
        "Numero piece",
        "Profession",
        "Lieu habitation",
        "Statut compte",
        "Jours restants",
        "Pourcentage validite",
        "Compte active le",
        "Compte expire le",
        "Nb reactivations",
        "Derniere reactivation par ID",
        "Derniere reactivation par email",
        "Derniere reactivation par nom",
        "Profil cree le",
        "Profil modifie le",
        "Compte cree le",
        "Compte modifie le",
    ]

    @staticmethod
    def _format_bool(value) -> str:
        return "Oui" if bool(value) else "Non"

    @staticmethod
    def _format_date(value) -> str:
        if not value:
            return ""
        return value.isoformat()

    @staticmethod
    def _format_datetime(value) -> str:
        if not value:
            return ""
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _row_from_etudiant(cls, etudiant) -> list[str]:
        user = etudiant.user
        reactive_par = getattr(etudiant, "derniere_reactivation_par", None)
        return [
            "Etudiant",
            str(etudiant.id),
            str(user.id),
            etudiant.matricule or "",
            user.first_name or "",
            user.last_name or "",
            user.get_full_name() or "",
            user.email or "",
            user.phone or "",
            cls._format_date(user.date_of_birth),
            user.user_type or "",
            cls._format_bool(user.is_active),
            cls._format_bool(user.is_2fa_enabled),
            cls._format_datetime(user.totp_verified_at),
            cls._format_datetime(user.last_login),
            user.avatar.name if user.avatar else "",
            str(etudiant.filiere_id or ""),
            getattr(etudiant.filiere, "name", "") or "",
            str(etudiant.niveau_id or ""),
            getattr(etudiant.niveau, "name", "") or "",
            str(etudiant.specialite_id or ""),
            getattr(etudiant.specialite, "name", "") or "",
            str(etudiant.annee_inscription or ""),
            "",
            "",
            "",
            etudiant.statut_compte or "",
            "" if etudiant.jours_restants is None else str(etudiant.jours_restants),
            "" if etudiant.pourcentage_validite is None else str(etudiant.pourcentage_validite),
            cls._format_datetime(etudiant.compte_active_le),
            cls._format_datetime(etudiant.compte_expire_le),
            str(etudiant.nb_reactivations),
            str(getattr(reactive_par, "id", "") or ""),
            getattr(reactive_par, "email", "") or "",
            reactive_par.get_full_name() if reactive_par else "",
            cls._format_datetime(etudiant.created_at),
            cls._format_datetime(etudiant.updated_at),
            cls._format_datetime(user.created_at),
            cls._format_datetime(user.updated_at),
        ]

    @classmethod
    def _row_from_personne_externe(cls, personne) -> list[str]:
        user = personne.user
        return [
            "Personne externe",
            str(personne.id),
            str(user.id),
            "",
            user.first_name or "",
            user.last_name or "",
            user.get_full_name() or "",
            user.email or "",
            user.phone or "",
            cls._format_date(user.date_of_birth),
            user.user_type or "",
            cls._format_bool(user.is_active),
            cls._format_bool(user.is_2fa_enabled),
            cls._format_datetime(user.totp_verified_at),
            cls._format_datetime(user.last_login),
            user.avatar.name if user.avatar else "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            personne.numero_piece or "",
            personne.profession or "",
            personne.lieu_habitation or "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            cls._format_datetime(personne.created_at),
            cls._format_datetime(personne.updated_at),
            cls._format_datetime(user.created_at),
            cls._format_datetime(user.updated_at),
        ]

    @classmethod
    def export(cls, etudiants, personnes_externes=None) -> bytes:
        rows = [cls._row_from_etudiant(etudiant) for etudiant in etudiants]
        if personnes_externes is not None:
            rows.extend(
                cls._row_from_personne_externe(personne)
                for personne in personnes_externes
            )
        return build_simple_xlsx(
            sheet_name="Profils",
            headers=cls.HEADERS,
            rows=rows,
        )
