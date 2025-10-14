from django.db import models

class PriceRecord(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    partner_id = models.BigIntegerField(db_index=True)
    dest = models.CharField(max_length=32, db_index=True)  # сейчас не используем, храним ""
    item_id = models.BigIntegerField(db_index=True)
    item_name = models.CharField(max_length=255)
    price_basic = models.IntegerField()     # ЦЕЛЫЕ рубли
    price_product = models.IntegerField()   # ЦЕЛЫЕ рубли

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
        ]
        ordering = ["-created_at", "partner_id", "dest", "item_id"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} | {self.partner_id} | {self.dest} | {self.item_name} ({self.item_id})"
