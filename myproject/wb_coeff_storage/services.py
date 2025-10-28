import os
import requests
from datetime import datetime
from django.utils import timezone

def get_wb_coef_storage(warehouse_id=None):
    """
    Тянет коэффициенты WB и строит матрицу по складам/датам
    (фильтруя только слоты с типом 'Короба', allowUnload=True и coefficient != -1).
    НИКАКИХ импортов моделей/БД — чтобы не падать при миграциях.
    """
    token = os.getenv("WB_API_TOKEN")
    if not token:
        raise ValueError("❌ Токен WB_API_TOKEN не найден в .env")

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    params = {}
    if warehouse_id:
        # WB ожидает строку с запятыми; для одного склада тоже строка
        params["warehouseIDs"] = str(warehouse_id)

    url = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Берём только Короба с разрешенной выгрузкой и валидным коэффициентом
        filtered = []
        for item in data:
            if (item.get("boxTypeName") != "Короба") or (not item.get("allowUnload", False)):
                continue
            coef = item.get("coefficient", -1)
            if coef == -1:
                continue
            filtered.append(item)

        # Уникальные склады и даты
        warehouses = sorted(set(i.get("warehouseName", "") for i in filtered))
        dates_raw = sorted(set(i.get("date") for i in filtered if i.get("date")))

        # Преобразуем даты в текст и заодно держим исходные ISO
        dates_iso = dates_raw
        dates_human = []
        for d in dates_iso:
            # WB присылает ISO UTC, например 2025-10-24T00:00:00Z
            try:
                dt = datetime.strptime(d, "%Y-%m-%dT%H:%M:%SZ")
                dt = timezone.make_aware(dt, timezone.utc).astimezone(timezone.get_current_timezone())
            except Exception:
                try:
                    tmp = datetime.fromisoformat(d.replace("Z", "+00:00"))
                    if tmp.tzinfo is None:
                        tmp = timezone.make_aware(tmp, timezone.utc)
                    dt = tmp.astimezone(timezone.get_current_timezone())
                except Exception:
                    dt = None
            dates_human.append(dt.strftime("%d.%m %A") if dt else d)

        # Заполним матрицу коэффициентов
        coeff_matrix = []
        for wh in warehouses:
            row = []
            for d in dates_iso:
                match = next(
                    (x for x in filtered if x.get("warehouseName") == wh and x.get("date") == d),
                    None
                )
                if match:
                    coef = match.get("coefficient", -1)
                    if coef != -1 and match.get("allowUnload", False):
                        row.append(coef)
                    else:
                        row.append("")
                else:
                    row.append("")
            coeff_matrix.append(row)

        return warehouses, dates_human, coeff_matrix

    except requests.RequestException as e:
        print("❌ Ошибка запроса:", e)
        return [], [], []
