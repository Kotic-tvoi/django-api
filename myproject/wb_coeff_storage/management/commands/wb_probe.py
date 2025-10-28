from django.core.management.base import BaseCommand
from wb_coeff_storage.management.commands.run_wb_bot import fetch_wb, normalize_slots, filter_interesting

class Command(BaseCommand):
    help = "Диагностика WB: показывает общее число валидных слотов и сколько прошло фильтры."

    def handle(self, *args, **opts):
        raw = fetch_wb()
        norm = normalize_slots(raw)
        got = len(norm)
        filt = filter_interesting(norm)
        self.stdout.write(self.style.SUCCESS(f"Валидных слотов (Короба/allowUnload/coef!=-1): {got}"))
        self.stdout.write(self.style.SUCCESS(f"Прошло фильтры (ID/имя/coef): {len(filt)}"))

        # примеры по совпавшим складам
        seen = set()
        for s in filt:
            if s['warehouseName'] in seen:
                continue
            seen.add(s['warehouseName'])
            self.stdout.write(
                f"• {s['warehouseName']} — {s['date_dt'].strftime('%d.%m %H:%M')} "
                f"coef={s['coefficient']}"
            )
            if len(seen) >= 5:
                break
