import requests
import re
import cloudscraper
from .pydantic_models import Items


class ParseWB:
    def __init__(self, url: str, dest: str = '-1275551'):
        self.seller_id = self.__get_seller_id(url)
        self.dest = str(dest)
        # создаём scraper вместо requests.Session()
        self.session = cloudscraper.create_scraper(browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True
        })

    @staticmethod
    def __get_seller_id(url: str):
        regex = r'(?<=seller/)\d+'
        seller_id = re.search(regex, url)[0]
        return seller_id
    

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
            }

            try:
                response = self.session.get(
                    f"https://www.wildberries.ru/__internal/catalog/sellers/v4/catalog",
                    headers=self._headers(),
                    params=params
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

        return Items(products=all_products)