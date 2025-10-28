from django.db import models

class PriceRecord(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    partner_id = models.BigIntegerField(db_index=True)
    partner_name = models.CharField(max_length=100, default="", db_index=True)
    # id ПВЗ (откуда смотрим цены)
    dest = models.CharField(max_length=32, db_index=True)  # сейчас не используем, храним
    item_id = models.BigIntegerField(db_index=True)
    item_name = models.CharField(max_length=255)
    article = models.CharField(max_length=64, default="", db_index=True)
    # начальная цена
    price_basic = models.IntegerField()
    price_before_spp = models.IntegerField()
    # Конечная цена      
    price_product = models.IntegerField()

    class Meta:
        # защищаемся от дублей в рамках одного запуска
        db_table = "API_ShowPrice_pricerecord" 
        constraints = [
            models.UniqueConstraint(
                fields=["created_at", "partner_id", "dest", "item_id"],
                name="uniq_snapshot_partner_dest_item"
            )
        ]
        indexes = [
            models.Index(fields=["created_at", "partner_id", "dest"]),
            models.Index(fields=["item_id"]),
            models.Index(fields=["partner_name"]),
            models.Index(fields=["article"]),
        ]
        ordering = ["-created_at", "partner_id", "dest", "item_id"]
