from django.db import migrations, models
from django.db.models import F

def fill_price_before_spp(apps, schema_editor):
    PriceRecord = apps.get_model("price_history_view", "PriceRecord")
    # где NULL — проставим = price_basic
    PriceRecord.objects.filter(price_before_spp__isnull=True)\
        .update(price_before_spp=F("price_basic"))

class Migration(migrations.Migration):

    dependencies = [
        ("price_history_view", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pricerecord",
            name="article",
            field=models.CharField(max_length=64, default="", blank=True),
        ),
        migrations.AddField(
            model_name="pricerecord",
            name="partner_name",
            field=models.CharField(max_length=100, default="", blank=True),
        ),
        # 1) добавляем поле как NULLable БЕЗ default
        migrations.AddField(
            model_name="pricerecord",
            name="price_before_spp",
            field=models.IntegerField(null=True, blank=True),
        ),
        # 2) заполняем данными (до СПП = basic)
        migrations.RunPython(fill_price_before_spp, migrations.RunPython.noop),
        # 3) ужесточаем схему: NOT NULL
        migrations.AlterField(
            model_name="pricerecord",
            name="price_before_spp",
            field=models.IntegerField(),
        ),
    ]
