# price_history_view/models.py
from django.db import models

class PriceRecord(models.Model):
    created_at   = models.DateTimeField(auto_now_add=True, db_index=True)
    partner_id   = models.BigIntegerField(db_index=True)
    partner_name = models.CharField(max_length=100, default="", db_index=True)

    # ПВЗ/регион – сохраняем, но не выводим в интерфейсе
    dest         = models.CharField(max_length=32, db_index=True, blank=True, default="")

    item_id      = models.BigIntegerField(db_index=True)
    item_name    = models.CharField(max_length=255)
    article      = models.CharField(max_length=64, default="", db_index=True)

    price_basic       = models.IntegerField()
    price_before_spp  = models.IntegerField(null=True, blank=True)  # пока заглушка
    price_product     = models.IntegerField()

    class Meta:
        db_table = "API_ShowPrice_pricerecord"
        constraints = [
            models.UniqueConstraint(
                fields=["created_at", "partner_id", "dest", "item_id"],
                name="uniq_snapshot_partner_dest_item",
            )
        ]
        indexes = [
            models.Index(fields=["created_at", "partner_id", "dest"]),
            models.Index(fields=["item_id"]),
            models.Index(fields=["partner_name"]),
            models.Index(fields=["article"]),
        ]
        ordering = ["-created_at", "partner_id", "dest", "item_id"]
