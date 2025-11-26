import requests
import os
import re
from dotenv import load_dotenv
from .pydantic_models import Items

load_dotenv()

PROXY = os.getenv("PROXY")
COOKIE = os.getenv("WB_COOKIE")
BEARER = os.getenv("WB_BEARER")


class ParseWB:
    def __init__(self, url: str, dest: str = "-1275551"):
        self.seller_id = self.__get_seller_id(url)
        self.dest = str(dest)

        self.session = requests.Session()

        # self.session.proxies.update({
        #     "http": PROXY,
        #     "https": PROXY,
        # })

        # устанавливаем cookies вручную
        self.session.headers.update({
            "Cookie": COOKIE
        })

    @staticmethod
    def __get_seller_id(url: str):
        return re.search(r'(?<=seller/)\d+', url)[0]

    def _headers(self):
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": f"https://www.wildberries.ru/seller/{self.seller_id}",
            "Origin": "https://www.wildberries.ru",

            # ОБЯЗАТЕЛЬНЫЕ заголовки
            "Authorization": f"Bearer {BEARER}",
            "X-Requested-With": "XMLHttpRequest",
            "X-SPA-Version": "13.14.1",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        }

    def get_items(self):

        page = 1
        all_products = []

        while True:
            params = {
                "appType": "1",
                "curr": "rub",
                "dest": self.dest,
                "lang": "ru",
                "page": page,
                "sort": "popular",
                "spp": "30",
                "supplier": self.seller_id,
                "uclusters": "3",
                "fbrand": "279103"
            }

            response = self.session.get(
                "https://www.wildberries.ru/__internal/catalog/sellers/v4/catalog",
                headers=self._headers(),
                params=params,
                timeout=20
            )

            if response.status_code == 498:
                print("⚠️ WB требуется challenge → cookie/bearer протухли.")
                break

            if response.status_code != 200:
                print("⚠️ Ошибка:", response.status_code)
                print(response.text[:200])
                break

            data = response.json()
            items = Items.model_validate(data)

            if not items.products:
                break

            all_products.extend(items.products)
            page += 1

        return Items(products=all_products)
