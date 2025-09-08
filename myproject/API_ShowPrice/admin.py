from django.contrib import admin
from .models import PriceRecord

@admin.register(PriceRecord)
class PriceRecordAdmin(admin.ModelAdmin):
    list_display = ("created_at", "partner_id", "dest", "item_id", "item_name", "price_basic", "price_product")
    list_filter = ("partner_id", "dest", "created_at")
    search_fields = ("item_name", "item_id")
    date_hierarchy = "created_at"
