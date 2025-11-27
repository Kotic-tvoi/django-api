# ozon.py

#!/usr/bin/env python3

import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from .xpaths import XPATHS

# === Настройки Selenium ===
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
)
chrome_options.add_argument("--disable-images")
chrome_options.add_argument("--blink-settings=imagesEnabled=false")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-extensions")

chrome_prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.stylesheets": 2,
    "profile.managed_default_content_settings.fonts": 2,
    "profile.managed_default_content_settings.javascript": 1,
}
chrome_options.add_experimental_option("prefs", chrome_prefs)

# ⚠️ поправь путь под свой сервер/окружение
service = Service(ChromeDriverManager().install())

# === Хелперы ===
def is_page_available(driver, timeout=2):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return True
    except Exception:
        return False


def get_element(driver, xpaths, default=None, timeout=2):
    for xpath in xpaths:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element.text.strip()
        except Exception:
            continue
    return default


def clear_price(value: str):
    """
    '2 369 ₽' → 2369 (int) или None
    """
    if not value:
        return None
    try:
        clean = (
            value.replace("₽", "")
            .replace("\u2009", "")  # &thinsp;
            .replace("\xa0", "")  # неразрывный пробел
            .replace(" ", "")
            .strip()
        )
        return int(clean)
    except ValueError:
        return None


def _parse_with_driver(driver, article: str) -> dict:
    """
    Логика один-в-один с твоей parse_product_page,
    только без сохранения в БД: просто возвращаем dict.
    """
    url = f"https://www.ozon.ru/product/{article}/"
    driver.get(url)

    if not is_page_available(driver, timeout=2):
        return {
            "article": str(article),
            "price": None,
            "card_price": None,
        }

    price = clear_price(get_element(driver, XPATHS["price"]))
    card_price = clear_price(get_element(driver, XPATHS["card_price"]))


    return {
        "article": str(article),
        "price": price,
        "card_price": card_price,
    }


# === Парсинг одного артикула (без многопоточности) ===
def parse_ozon(article: str) -> dict:
    temp_dir = tempfile.TemporaryDirectory()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        data = _parse_with_driver(driver, article)
    finally:
        driver.quit()
        temp_dir.cleanup()

    return data


# === Многопоточный парсинг нескольких артикулов ===
def parse_ozon_many(articles, max_threads: int = 3):
    """
    articles: список артикулов (строки или числа)
    возвращает: список dict в том же порядке, что и вход.
    """

    articles = list(articles)
    results = [None] * len(articles)

    def worker(idx, article):
        temp_dir = tempfile.TemporaryDirectory()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        try:
            data = _parse_with_driver(driver, article)
        except Exception as e:
            # на всякий случай, чтобы не падать целиком
            data = {
                "article": str(article),
                "price": None,
                "card_price": None,
                "rating": None,
            }
        finally:
            driver.quit()
            temp_dir.cleanup()
        return idx, data

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [
            executor.submit(worker, idx, article)
            for idx, article in enumerate(articles)
        ]
        for fut in as_completed(futures):
            idx, data = fut.result()
            results[idx] = data

    return results
