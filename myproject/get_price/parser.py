import os
import re
from pathlib import Path

import requests
from django.conf import settings
from dotenv import dotenv_values

from .pydantic_models import Items


ENV_PATH = Path(settings.BASE_DIR) / ".env"
PROXY = os.getenv("PROXY")


class ParseWB:
    def __init__(self, url: str, dest: str = "1259571021"):
        self.seller_id = self.__get_seller_id(url)
        self.dest = str(dest)
        self.session = requests.Session()

        # Если нужен proxy — раскомментировать
        # self.session.proxies.update({
        #     "http": PROXY,
        #     "https": PROXY,
        # })

    @staticmethod
    def __get_seller_id(url: str):
        return re.search(r"(?<=seller/)\d+", url)[0]

    @staticmethod
    def _normalize_bearer(value: str) -> str:
        value = (value or "").strip().strip('"').strip("'")

        if value.lower().startswith("bearer "):
            value = value.split(" ", 1)[1].strip()

        return value

    @staticmethod
    def _get_auth_from_env():
        """
        Читаем WB_COOKIE/WB_BEARER из .env при каждом запросе.
        Поэтому после POST-обновления не нужен перезапуск Django.
        """
        values = dotenv_values(ENV_PATH)

        cookie = (values.get("WB_COOKIE", "") or "").strip().strip('"').strip("'")
        bearer = ParseWB._normalize_bearer(values.get("WB_BEARER", "") or "")

        return cookie, bearer

    def _headers(self):
        cookie, bearer = self._get_auth_from_env()

        headers = {
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-GB;q=0.8,en;q=0.7,en-US;q=0.6",
            "Referer": f"https://www.wildberries.ru/seller/{self.seller_id}",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "X-SPA-Version": "14.12.7",
            "Sec-CH-UA": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "DeviceID": "site_d95be25189e34823b7a6f57b3c6acea4",
        }

        if cookie:
            headers["Cookie"] = cookie

        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"

        return headers

    def _catalog_url(self):
        return "https://www.wildberries.ru/__internal/catalog/sellers/v4/catalog"

    def _params(self, page: int):
        return {
            "ab_testing": "false",
            "appType": "64",
            "curr": "rub",
            "dest": self.dest,
            "hide_dtype": "15",
            "hide_vflags": "4294967296",
            "lang": "ru",
            "mdg": "107",
            "page": page,
            "sort": "popular",
            "spp": "30",
            "supplier": self.seller_id,
            "uclusters": "3",
        }

    def get_items(self):
        page = 1
        all_products = []

        while True:
            response = self.session.get(
                self._catalog_url(),
                headers=self._headers(),
                params=self._params(page),
                timeout=20,
            )

            print("DEBUG WB URL:", response.url)
            print("DEBUG WB status:", response.status_code)

            if response.status_code != 200:
                print("⚠️ Ошибка:", response.status_code)
                print(response.text[:500])
                break

            data = response.json()
            items = Items.model_validate(data)

            if not items.products:
                break

            all_products.extend(items.products)
            page += 1

        return Items(products=all_products)