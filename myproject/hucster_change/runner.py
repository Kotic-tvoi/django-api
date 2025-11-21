import os, time, re, asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError
from dotenv import load_dotenv
from .constants import product_keys
import json


load_dotenv()
TAB_TEXT = "Удержание РЦ"
RUN_TEXT = "Отправить на проверку"
MP_HEADERS = {"ozon": "OZON (Ozon FBO)", "wb": "WB (WB FBS-FBW)"}

EMAIL_SEL = 'input[formcontrolname="email"]#email'
PASS_SEL  = 'input[formcontrolname="password"][type="password"]'
SUBMIT_BTN = 'button:has(span.p-button-label:has-text("ВОЙТИ"))'

KEY_RX = re.compile(r'^[a-f0-9]{32}$', re.IGNORECASE)

LOGIN = os.getenv("ETP_LOGIN")
PASSWORD = os.getenv("ETP_PASSWORD")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

BASE_URL = os.getenv("HUCSTER_BASE_URL", "https://market.e-teleport.ru/catalog/")
STATE_FILE = "state.json"


def print_result_json(results: list[dict]):
    print(json.dumps(results, indent=4, ensure_ascii=False))

# Постройка url из ключа
def build_url_from_key(key: str) -> str:
    return BASE_URL.rstrip('/') + '/' + key

# Валидация ключа
def is_valid_key(key: str) -> bool:
    return bool(KEY_RX.fullmatch(key or ""))


async def first_time_login(context):
    """Логинимся один раз, сохраняем сессию в state.json"""
    page = await context.new_page()
    await page.goto(BASE_URL, wait_until="domcontentloaded")

    try:
        await page.wait_for_selector(EMAIL_SEL, timeout=1500)
    except:
        # Уже залогинены
        await context.storage_state(path=STATE_FILE)
        return

    await page.fill(EMAIL_SEL, LOGIN)
    await page.fill(PASS_SEL, PASSWORD)
    await page.click(SUBMIT_BTN)
    await page.wait_for_selector(EMAIL_SEL, state="detached", timeout=15000)

    await context.storage_state(path=STATE_FILE)


async def click_and_read_modal(page, header):
    """Чтение результата проверки"""
    modal = page.locator("div.p-dialog").filter(has_text=header).first
    await modal.wait_for(state="visible", timeout=80000)

    msg = modal.locator("div.p-dialog-content span.ng-star-inserted").first
    await msg.wait_for(state="visible", timeout=80000)

    text = (await msg.inner_text()).strip()

    # закрыть диалог
    try:
        await modal.locator('button:has-text("Закрыть")').click()
    except:
        pass

    return text


async def run_once_key(browser, key: str, mp_key: str) -> dict:
    start = time.time()
    url = build_url_from_key(key)

    context = await browser.new_context(
        locale="ru-RU",
        storage_state=STATE_FILE
    )
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded")

        # Вкладка
        tab = page.locator(f'span.p-tabview-title:has-text("{TAB_TEXT}")').first
        await tab.wait_for(state="visible", timeout=20000)
        await tab.click()

        header = MP_HEADERS[mp_key]
        title = page.locator(f"text={header}").first
        await title.wait_for(state="visible", timeout=20000)

        acc = title.locator('xpath=ancestor::p-accordiontab[1]')
        link = acc.locator('a.p-accordion-header-link').first
        if (await link.get_attribute("aria-expanded")) != "true":
            await link.click()

        btn = acc.locator(f'button:has-text("{RUN_TEXT}")').first
        await btn.wait_for(state="visible", timeout=80000)

        disabled = await btn.evaluate(
            'el => el.disabled || el.getAttribute("aria-disabled") === "true"'
        )
        if disabled:
            return {
                "key": key,
                "article": product_keys[key],
                "status": f"{header}: кнопка отключена",
                "elapsed": round(time.time() - start, 2)
            }

        await btn.click()

        # читаем результат
        msg_text = await click_and_read_modal(page, header)

        return {
            "key": key,
            "article": product_keys[key],
            # "status": f"{header}: {msg_text}",
            "msg_text": msg_text,
            "elapsed": round(time.time() - start, 2)
        }

    except Exception as e:
        return {
            "key": key,
            "article": product_keys[key],
            "status": f"Ошибка: {e!r}",
            "msg_text": f"{e!r}",
            "elapsed": round(time.time() - start, 2)
        }

    finally:
        await context.close()

# # Прямой запуск
# async def run_many_keys(keys: list[str], mp_key: str, concurrency: int = 3):
#     async with async_playwright() as pw:
#         # 1) запускаем один браузер
#         browser = await pw.chromium.launch(headless=HEADLESS)

#         # 2) логинимся только один раз
#         context = await browser.new_context(locale="ru-RU")
#         await first_time_login(context)
#         await context.close()

#         # 3) создаём семафор параллельности
#         sem = asyncio.Semaphore(concurrency)
#         results = []

#         async def worker(k):
#             async with sem:
#                 # каждый ключ получает отдельный контекст, но с cookie
#                 res = await run_once_key(browser, k, mp_key)
#                 results.append(res)

#         # 4) запускаем все задачи
#         await asyncio.gather(*(worker(k) for k in keys))

#         # 5) сортируем в том же порядке, что и вход
#         return [next(r for r in results if r["key"] == k) for k in keys]


async def run_many_keys_with_back(keys, mp_key, concurrency, max_retries):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)

        # Логинимся один раз
        context = await browser.new_context(locale="ru-RU")
        await first_time_login(context)
        await context.close()

        sem = asyncio.Semaphore(concurrency)

        async def run_key(key):
            async with sem:
                return await run_once_key(browser, key, mp_key)

        # начальная очередь
        queue = list(keys)
        results = []
        attempts = {k: 0 for k in keys}
        count_curcl = 1

        while queue:
            start_curcl = time.time()
            print(f"[BATCH] Запускаем пакет: {len(queue)} ключей")

            # Параллельный запуск пакета
            batch = queue
            queue = []

            batch_results = await asyncio.gather(*(run_key(k) for k in batch))

            for key, result in zip(batch, batch_results):
                attempts[key] += 1
                msg = result.get("msg_text", "").lower()

                is_timeout = "timeouterror" in msg
                is_failed_send = "не удалось отправить запрос" in msg

                if (is_failed_send or is_timeout) and attempts[key] <= max_retries:
                    # print(f"[RETRY] {key} → повторная очередь (попытка {attempts[key]})", flush=True)
                    queue.append(key)
                else:
                    # print(f"[OK] {result}", flush=True)
                    results.append(result)

            elapsed_min = (time.time() - start_curcl)
            print(f"{count_curcl} цикл шёл: {elapsed_min:.2f} секунд")
            count_curcl += 1
        return results
