import requests
import re
from .pydantic_models import Items

WB_CART = 2

dest_name= {
    'SPb': -1205339,
    'Сыктывкар': 123585595,
    'Казань': -2133462,
    'Москва': -1257786
}

partners = {
    550199: "Роман Трофимов",
    329266: "Голуб Дарья",
    77377: "Наталья Баринова",
    425347: "Анисимов Павел",
    1409657: "Мария Митина",
    1266117: "Alex Shchotski",
    826325: "Игорь",
    1383307: "Екатерина Прокофьева",
    533329: "Шелуханова Юлия",
    215484: "JKeratin",
}

class ParseWB:
    def __init__(self, url: str, dest: str = '-1257786'):
        self.seller_id = self.__get_seller_id(url)
        self.WB_CART = WB_CART
        self.dest = dest

    @staticmethod
    def __get_seller_id(url: str):
        regex = r'(?<=seller/)\d+'
        seller_id = re.search(regex, url)[0]
        return seller_id

    def get_items(self):
        _page = 1
        all_products = []

        while True:
            response = requests.get(
                'https://catalog.wb.ru/sellers/v2/catalog',
                params={
                    'appType': '1',
                    'curr': 'rub',
                    'dest': self.dest,
                    'lang': 'ru',
                    'page': _page,
                    'sort': 'popular',
                    'spp': '30',
                    'supplier': self.seller_id,
                    'uclusters': '3',
                    'brand': 279103
                }
            )
            _page += 1
            items_info = Items.model_validate(response.json()["data"])
            if not items_info.products:
                break
            all_products.extend(items_info.products)

        return Items(products=all_products)
