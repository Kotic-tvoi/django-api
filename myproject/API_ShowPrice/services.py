# myapp/services.py
import os
import requests
from datetime import datetime, timedelta
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


    params = {}
    if warehouse_id:
        params["warehouseIDs"] = warehouse_id

    url = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Фильтруем только "Короба"
        filtered = [item for item in data if item.get("boxTypeName") == "Короба"]

        # Получаем уникальные склады и даты
        warehouses = sorted(set(item["warehouseName"] for item in filtered))
        dates = sorted(set(item["date"] for item in filtered))

        # Преобразуем даты в формат дд.мм день недели
        formatted_dates = []
        for d in dates:
            dt = datetime.strptime(d, "%Y-%m-%dT%H:%M:%SZ")
            formatted = dt.strftime("%d.%m %A")
            formatted_dates.append(formatted)

        # Готовим пустую таблицу коэффициентов
        coeff_matrix = []

        for warehouse in warehouses:
            row = []
            for d in dates:
                # Ищем запись с этим складом и датой
                match = next((item for item in filtered if item["warehouseName"] == warehouse and item["date"] == d), None)
                if match:
                    coef = match["coefficient"]
                    if coef != -1 and match.get("allowUnload") == True:
                        row.append(coef)
                    else:
                        row.append("")
                else:
                    row.append("")
            coeff_matrix.append(row)

        # Возвращаем результат в нужной структуре
        return warehouses, formatted_dates, coeff_matrix

    except requests.RequestException as e:
        print("❌ Ошибка запроса:", e)
        return {
            "warehouses": [],
            "dates": [],
            "matrix": []
        }
    # try:
    #     response = requests.get(url, headers=headers, params=params)
    #     response.raise_for_status()
    #     data = response.json()

    #     # Фильтруем только данные по коробам
    #     today_date = datetime.today()
    #     date_list = [(today_date + timedelta(days=i)).strftime("%d.%m %A") for i in range(14)]
    #     storage_list = []
    #     quef_list = []
    #     n = 0
    #     for item in data:
    #         if (item.get("boxTypeName") == "Короба"):
    #             storage_name = item.get("warehouseName")
    #             if storage_name not in storage_list:
    #                 storage_list.append(storage_name)
                 



            
    #         # if (item.get("boxTypeName") == "Короба"):

    #         #     if (
    #         #         item.get("coefficient") != -1 and
    #         #         item.get("allowUnload") == True
    #         #     ):
    #         #         boxes_only.append(
    #         #             {
    #         #             "date": item.get("date"),
    #         #             "warehouseName": item.get("warehouseName"),
    #         #             "coefficient": item.get("coefficient"),
    #         #             }
    #         #             )
    #         #     else:
    #         #         boxes_only.append(
    #         #             {
    #         #             "date": item.get("date"),
    #         #             "warehouseName": item.get("warehouseName"),
    #         #             "coefficient": "",
    #         #             }
    #         #             )

    #     # boxes_only = [item for item in data if item.get("boxTypeName")]

    #     return boxes_only
    # except requests.RequestException as e:
    #     print("❌ Ошибка запроса:", e)
    #     return []
