import sqlite3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager

from .xpaths import XPATHS


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--window-size=1920,1080")

    # отключаем подгрузку ресурсов
    chrome_prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.javascript": 1
    }
    chrome_options.add_experimental_option("prefs", chrome_prefs)

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )


def get_el(driver, xpaths, timeout=2):
    for xpath in xpaths:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return el.text.strip()
        except Exception:
            continue
    return None


def clear_price(v):
    if not v:
        return None
    v = (
        v.replace("₽", "")
         .replace("\u2009", "")
         .replace("\xa0", "")
         .replace(" ", "")
         .strip()
    )
    try:
        return int(v)
    except:
        return None


def parse_article(article):
    driver = create_driver()

    try:
        url = f"https://www.ozon.ru/product/{article}/"
        driver.get(url)

        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ts = int(datetime.now().timestamp())

        price = clear_price(get_el(driver, XPATHS["price"]))
        card_price = clear_price(get_el(driver, XPATHS["card_price"]))
        # rating = get_el(driver, XPATHS["rating"])
        # reviews = get_el(driver, XPATHS["reviews_count"])
        # questions = get_el(driver, XPATHS["questions_count"])

        return {
            "article": article,
            "date": date,
            "timestamp": ts,
            "price": price,
            "card_price": card_price,
            # "rating": rating,
            # "reviews": int(''.join(filter(str.isdigit, reviews))) if reviews else 0,
            # "questions": int(''.join(filter(str.isdigit, questions))) if questions else 0,
            # "available": 1 if price else 0,
        }

    finally:
        driver.quit()
