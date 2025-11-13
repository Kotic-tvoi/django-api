import re
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from .pydantic_models import Items

executor = ThreadPoolExecutor(max_workers=1)  # один поток для Playwright


class ParseWB:
    def __init__(self, url: str, dest: str = '-1275551'):
        self.url = url
        self.dest = str(dest)
        self.seller_id = self.__get_seller_id(url)

    @staticmethod
    def __get_seller_id(url: str):
        m = re.search(r"(?<=seller/)\d+", url)
        if not m:
            raise ValueError(f"Не найден seller_id в ссылке: {url}")
        return m.group(0)

    # ---- Главное изменение — перенос Playwright в поток ----
    def _run_in_thread(self, func, *args, **kwargs):
        return executor.submit(func, *args, **kwargs).result()

    # Теперь get_items запускаем внутри потока, чтобы Django ASGI не ругался
    def get_items(self):
        return self._run_in_thread(self._get_items_playwright)

    # ---- Синхронный метод, который реально работает с Playwright ----
    def _get_items_playwright(self):
        play = sync_playwright().start()

        browser = play.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()
        page.goto("https://www.wildberries.ru", timeout=60000)

        base_url = "https://www.wildberries.ru/__internal/catalog/sellers/v4/catalog"

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

            response = context.request.get(base_url, params=params)
            if response.status != 200:
                print("⚠️ Ошибка WB:", response.status)
                break

            data = response.json()
            items_info = Items.model_validate(data)

            if not items_info.products:
                break

            all_products.extend(items_info.products)
            _page += 1

        # корректно закрываем playwright
        context.close()
        browser.close()
        play.stop()

        return Items(products=all_products)
