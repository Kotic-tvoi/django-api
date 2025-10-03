import os, time, re, asyncio
from django.conf import settings
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

TAB_TEXT = "Репрайсер. Удержание РЦ"
RUN_TEXT = "Отправить на проверку"
MP_HEADERS = {"ozon": "OZON (Ozon FBO)", "wb": "WB (WB FBS-FBW)"}

EMAIL_SEL = 'input[formcontrolname="email"]#email'
PASS_SEL  = 'input[formcontrolname="password"][type="password"]'
SUBMIT_BTN = 'button:has(span.p-button-label:has-text("ВОЙТИ"))'

KEY_RX = re.compile(r'^[a-f0-9]{32}$', re.IGNORECASE)

LOGIN = os.getenv("ETP_LOGIN")
PASSWORD = os.getenv("ETP_PASSWORD")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
BASE_URL = getattr(settings, "HUCSTER_BASE_URL", "https://market.e-teleport.ru/catalog/")

def build_url_from_key(key: str) -> str:
    return BASE_URL.rstrip('/') + '/' + key

def is_valid_key(key: str) -> bool:
    return bool(KEY_RX.fullmatch(key or ""))

async def _simple_login_if_form(page):
    try:
        await page.wait_for_selector(EMAIL_SEL, timeout=1500)
    except PWTimeoutError:
        return
    if not (LOGIN and PASSWORD):
        raise RuntimeError("Нужно задать ETP_LOGIN и ETP_PASSWORD в .env")
    await page.fill(EMAIL_SEL, LOGIN)
    await page.fill(PASS_SEL, PASSWORD)
    try:
        await page.click(SUBMIT_BTN, timeout=5000)
    except PWTimeoutError:
        span = page.locator('span.p-button-label:has-text("ВОЙТИ")').first
        await span.evaluate('el => (el.closest("button") || el).click()')
    try:
        await page.wait_for_selector(EMAIL_SEL, state="detached", timeout=15000)
    except PWTimeoutError:
        pass

async def _click_reprice_for_mp(page, mp_key: str) -> str:
    header = MP_HEADERS.get(mp_key)
    if not header:
        return f"Неизвестный МП: {mp_key} (ожидаю 'ozon' или 'wb')"

    tab = page.locator(f'span.p-tabview-title:has-text("{TAB_TEXT}")').first
    await tab.wait_for(state="visible", timeout=20000)
    await tab.evaluate('el => (el.closest("a") || el.closest("li") || el).click()')

    title = page.locator(f'span.header-text:has-text("{header}")').first
    await title.wait_for(state="visible", timeout=20000)
    await title.scroll_into_view_if_needed()

    acc = title.locator('xpath=ancestor::p-accordiontab[1]')
    try:
        link = acc.locator('a.p-accordion-header-link').first
        expanded = await link.get_attribute("aria-expanded")
        if expanded in (None, "false"):
            await link.click()
    except Exception:
        pass

    btn = acc.locator(f'button:has(span.p-button-label:has-text("{RUN_TEXT}"))').first
    await btn.wait_for(state="attached", timeout=10000)
    await btn.scroll_into_view_if_needed()

    disabled = await btn.evaluate('el => el.disabled || el.getAttribute("aria-disabled") === "true"')
    if disabled:
        return f"{header}: кнопка отключена"

    await btn.click()
    await page.wait_for_timeout(500)
    return f"{header}: отправлено на проверку"

async def run_once_key(key: str, mp_key: str) -> dict:
    """Собираем URL из ключа и выполняем клик."""
    start = time.time()
    url = build_url_from_key(key)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS, slow_mo=150)
        context = await browser.new_context(locale="ru-RU")
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        await _simple_login_if_form(page)
        await page.goto(url, wait_until="domcontentloaded")

        try:
            status = await _click_reprice_for_mp(page, mp_key)
        except Exception as e:
            status = f"Ошибка: {e!r}"
        await browser.close()

    return {
        "key": key,
        "url": url,
        "mp": mp_key,
        "status": status,
        "elapsed_sec": round(time.time() - start, 2),
    }

async def run_many_keys(keys: list[str], mp_key: str, concurrency: int = 3) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    results: list[dict] = []

    async def worker(k: str):
        async with sem:
            try:
                res = await run_once_key(k, mp_key)
            except Exception as e:
                res = {"key": k, "url": build_url_from_key(k), "mp": mp_key, "status": f"Ошибка: {e!r}"}
            results.append(res)

    await asyncio.gather(*(worker(k) for k in keys))
    results.sort(key=lambda r: keys.index(r["key"]))  # сохранить порядок клиента
    return results
