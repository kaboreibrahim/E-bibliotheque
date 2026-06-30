from django.db import models

from apps.documents.utils import BYTES_PER_MEGABYTE, format_file_size


class DocumentStorageConfiguration(models.Model):
    singleton_pk = 1

    server_disk_capacity_mb = models.PositiveBigIntegerField(
        default=0,
        verbose_name="Capacite disque du serveur (Mo)",
        help_text="Capacite totale du disque dedie au stockage des documents, en Mo.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Configuration de stockage document"
        verbose_name_plural = "Configuration de stockage document"

    @classmethod
    def get_solo(cls):
        configuration, _ = cls.objects.get_or_create(
            pk=cls.singleton_pk,
            defaults={"server_disk_capacity_mb": 0},
        )
        return configuration

    @property
    def server_disk_capacity_bytes(self) -> int:
        return int(self.server_disk_capacity_mb or 0) * BYTES_PER_MEGABYTE

    @property
    def server_disk_capacity_display(self) -> str:
        return format_file_size(self.server_disk_capacity_bytes)

    def save(self, *args, **kwargs):
        self.pk = self.singleton_pk
        super().save(*args, **kwargs)

    def __str__(self):
        return "Configuration stockage documents"
