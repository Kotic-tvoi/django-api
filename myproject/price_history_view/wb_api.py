# price_history_view/wb_api.py
import os
import logging
import requests
from typing import Iterable

log = logging.getLogger(__name__)

API_URL = "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter"

def _get_token() -> str | None:
    # принимаем оба имени переменной окружения
    return os.getenv("WB_DISCOUNTS_API_TOKEN") or os.getenv("WB_API_TOKEN")

def _chunks(seq: list[int], n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def _try_request(nmids: list[int], token: str) -> dict[int, int] | None:
    """
    Пытаемся несколькими способами (часть инсталляций WB требует Bearer, часть — нет),
    и детально логируем ответ при ошибке.
    Возвращаем map {nmID: price_before_spp} либо None, если все попытки неудачны.
    """
    headers_variants = [
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        {"Authorization": token, "Content-Type": "application/json"},
    ]
    bodies = [
        {"nmIDs": nmids},                    # самый вероятный формат
        {"filterNmIDs": nmids},              # альтернативное имя поля
    ]
    # иногда встречается GET c nmIDs через ';'
    get_params = {"nmIDs": ";".join(str(x) for x in nmids)}

    # 1) POST варианты
    for h in headers_variants:
        for body in bodies:
            try:
                r = requests.post(API_URL, json=body, headers=h, timeout=15)
                if r.status_code == 200:
                    return _parse_prices(r.json())
                else:
                    log.warning("WB API POST failed %s, body=%s, headers=%s, text=%s",
                                r.status_code, body, {"Authorization": h.get("Authorization")}, r.text[:500])
            except Exception as e:
                log.exception("WB API POST exception: %s", e)

    # 2) GET вариант
    for h in headers_variants:
        try:
            r = requests.get(API_URL, params=get_params, headers=h, timeout=15)
            if r.status_code == 200:
                return _parse_prices(r.json())
            else:
                log.warning("WB API GET failed %s, params=%s, headers=%s, text=%s",
                            r.status_code, get_params, {"Authorization": h.get("Authorization")}, r.text[:500])
        except Exception as e:
            log.exception("WB API GET exception: %s", e)

    return None

def _parse_prices(payload: dict) -> dict[int, int]:
    """
    Ожидаем форму:
    {
      "data": {
        "listGoods": [
          {"nmID": 98486, "sizes":[{"price":500, "discountedPrice":350, ...}]},
          ...
        ]
      },
      "error": false, "errorText": ""
    }
    Возвращаем {nmID: price} где price = "цена до СПП".
    Берём из sizes[0].price (по твоему примеру это она и есть).
    """
    result: dict[int, int] = {}
    try:
        data = payload.get("data") or {}
        goods = data.get("listGoods") or []
        for g in goods:
            nm = int(g.get("nmID"))
            sizes = g.get("sizes") or []
            if not sizes:
                continue
            # цена до СПП — поле "price" (целое число в рублях по твоему примеру)
            price_before = sizes[0].get("price")
            if price_before is None:
                continue
            # округлим до int на всякий
            result[nm] = int(round(float(price_before)))
    except Exception as e:
        log.exception("WB API parse error: %s; payload head=%s", e, str(payload)[:400])
    return result

def fetch_prices_before_spp(nmids_iter: Iterable[int]) -> dict[int, int]:
    """
    Публичная функция: принимает nmIDs, бьёт на батчи, агрегирует цены.
    Возвращает {nmID: price_before_spp}.
    """
    token = _get_token()
    if not token:
        log.warning("WB token not set (WB_DISCOUNTS_API_TOKEN / WB_API_TOKEN)")
        return {}

    nmids = list({int(x) for x in nmids_iter if x})
    result: dict[int, int] = {}
    if not nmids:
        return result

    for batch in _chunks(nmids, 50):  # безопасный размер батча
        data = _try_request(batch, token)
        if data is None:
            # уже залогировали детали в _try_request
            continue
        result.update(data)

    return result
