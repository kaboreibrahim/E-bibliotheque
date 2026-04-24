import uuid

from django.db import migrations, models
import django.db.models.deletion


DEFAULT_TYPE_DOCUMENTS = [
    ("EXAMEN", "Examen"),
    ("MEMOIRE", "Memoire"),
    ("THESE", "These"),
    ("COURS", "Cours"),
]


def _normalize_code(value):
    if value is None:
        return ""
    return str(value).strip().upper()


def _build_name(code):
    labels = dict(DEFAULT_TYPE_DOCUMENTS)
    return labels.get(code, code.replace("_", " ").title())


def forwards(apps, schema_editor):
    TypeDocument = apps.get_model("documents", "TypeDocument")
    Document = apps.get_model("documents", "Document")
    db_alias = schema_editor.connection.alias

    for code, name in DEFAULT_TYPE_DOCUMENTS:
        TypeDocument.objects.using(db_alias).get_or_create(
            code=code,
            defaults={"name": name},
        )

    fallback_type, _ = TypeDocument.objects.using(db_alias).get_or_create(
        code="AUTRE",
        defaults={"name": "Autre"},
    )

    for raw_code in (
        Document.objects.using(db_alias)
        .exclude(type__isnull=True)
        .values_list("type", flat=True)
        .distinct()
    ):
        code = _normalize_code(raw_code)
        if not code:
            continue

        TypeDocument.objects.using(db_alias).get_or_create(
            code=code,
            defaults={"name": _build_name(code)},
        )

    for document in Document.objects.using(db_alias).all():
        code = _normalize_code(getattr(document, "type", None))
        if not code:
            document.type_document_id = fallback_type.id
        else:
            document_type = TypeDocument.objects.using(db_alias).get(code=code)
            document.type_document_id = document_type.id
        document.save(update_fields=["type_document"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0007_alter_document_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="TypeDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=100, unique=True, verbose_name="Code")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Libelle")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Cree le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modifie le")),
            ],
            options={
                "verbose_name": "Type de document",
                "verbose_name_plural": "Types de documents",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="document",
            name="type_document",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="documents",
                to="documents.typedocument",
                verbose_name="Type de document",
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="document",
            name="type",
        ),
        migrations.RenameField(
            model_name="document",
            old_name="type_document",
            new_name="type",
        ),
        migrations.AlterField(
            model_name="document",
            name="type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="documents",
                to="documents.typedocument",
                verbose_name="Type de document",
            ),
        ),
    ]
