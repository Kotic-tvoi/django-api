# myapp/services.py
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def get_wb_coef_storage(warehouse_id=None):
    token = os.getenv("WB_API_TOKEN")
    if not token:
        raise ValueError("❌ Токен WB_API_TOKEN не найден в .env")

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    today_date = datetime.today().strftime("%Y-%m-%d")

    params = {}
    if warehouse_id:
        params["warehouseIDs"] = warehouse_id
    params["date"] = today_date

    url = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Фильтруем только данные по коробам
        boxes_only = []
        for item in data:
            if (item.get("boxTypeName") == "Короба"):

                if (
                    item.get("coefficient") != -1 and
                    item.get("allowUnload") == True
                ):
                    boxes_only.append(
                        {
                        "date": item.get("date"),
                        "warehouseName": item.get("warehouseName"),
                        "coefficient": item.get("coefficient"),
                        }
                        )
                else:
                    boxes_only.append(
                        {
                        "date": item.get("date"),
                        "warehouseName": item.get("warehouseName"),
                        "coefficient": "",
                        }
                        )

        # boxes_only = [item for item in data if item.get("boxTypeName")]

        return boxes_only
    except requests.RequestException as e:
        print("❌ Ошибка запроса:", e)
        return []
