import requests
import os
import re
import cloudscraper
from .pydantic_models import Items
from dotenv import load_dotenv



load_dotenv()
PROXY = os.getenv("PROXY")

class ParseWB:
    def __init__(self, url: str, dest: str = '-1275551'):
        self.seller_id = self.__get_seller_id(url)
        self.dest = str(dest)

        # создаём scraper как раньше
        self.session = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "desktop": True
            }
        )

        # 🔥 добавляем прокси тут (ПРАВИЛЬНО!)
        self.session.proxies.update({
            "http": PROXY,
            "https": PROXY,
        })

        # пробуем получить токены WB
        try:
            resp = self.session.get("https://www.wildberries.ru", timeout=10)
            self.session.cookies.update(resp.cookies)
            print("🍪 WB cookies и токен получены:", list(resp.cookies.get_dict().keys()))
        except Exception as e:
            print("⚠️ Не удалось инициализировать сессию WB:", e)


    @staticmethod
    def __get_seller_id(url: str):
        regex = r'(?<=seller/)\d+'
        return re.search(regex, url)[0]
    

    def _headers(self):
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://www.wildberries.ru/seller/{self.seller_id}",
            "Origin": "https://www.wildberries.ru",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

    def get_items(self):
        _page = 1
        all_products = []

        while True:
            params = {
                "appType": "1",
                "curr": "rub",
                "dest": self.dest,
                "lang": "ru",
                "page": _page,
                "sort": "popular",
                "spp": "30",
                "supplier": self.seller_id,
                "uclusters": "3",
                "fbrand": "279103"
            }

            try:
                response = self.session.get(
                    "https://www.wildberries.ru/__internal/catalog/sellers/v4/catalog",
                    headers=self._headers(),
                    params=params,
                    timeout=20
                )

                if response.status_code != 200:
                    print(f"⚠️ Ошибка WB: {response.status_code}")
                    print(response.text[:200])
                    break

                items_info = Items.model_validate(response.json())
                if not items_info.products:
                    break

                all_products.extend(items_info.products)
                _page += 1

            except requests.RequestException as e:
                print("⚠️ Ошибка запроса:", e)
                break

        return Items(products=all_products)
