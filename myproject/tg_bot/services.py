import os
import requests


def get_filtered_warehouses():
    """
    Получает от Wildberries список складов с типом 'Короб',
    у которых коэффициент != -1 и разрешена выгрузка.
    Возвращает список уникальных названий складов.
    """
    token = os.getenv("WB_API_TOKEN")
    if not token:
        raise ValueError("❌ Токен WB_API_TOKEN не найден в .env")

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    url = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"❌ Ошибка при запросе к WB API: {e}")
        return []

    # Фильтрация по условиям
    filtered = [item for item in data if item.get("boxTypeName") == "Короба"]

    # # Уникальные названия складов
    # warehouses = sorted(set(item["warehouseName"] for item in filtered))
    # return warehouses

    seen_ids = set()
    warehouses = []
    warehouse_map = {}

    for item in filtered:
        warehouse_id = item.get("warehouseID")
        name = item.get("warehouseName")
        if warehouse_id not in seen_ids:
            seen_ids.add(warehouse_id)
            warehouses.append(name)
            warehouse_map[warehouse_id] = name

    return sorted(warehouses), warehouse_map