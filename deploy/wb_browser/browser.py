#!/usr/bin/env python3
"""Isolated WB browser on a virtual X display (manual login via noVNC).

No Django integration, no cookie export, no background scraping.
"""
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Error, TimeoutError, sync_playwright

HOME = Path.home()
PROFILE = HOME / ".local" / "share" / "wb-vps-browser" / "profile"
WB_URL = "https://www.wildberries.ru/"


def catalog_response(response):
    parsed = urlsplit(response.url)
    if (
        parsed.hostname == "www.wildberries.ru"
        and parsed.path == "/__internal/catalog/sellers/v4/catalog"
    ):
        params = parse_qs(parsed.query)
        partner = params.get("supplier", ["?"])[0]
        dest = params.get("dest", ["?"])[0]
        # Never log URL, cookies, Authorization, response body, or session tokens.
        print(f"[WB catalog] status={response.status} partner={partner} dest={dest}", flush=True)


def main():
    if os.geteuid() == 0:
        raise SystemExit("Do not launch a browser as root.")
    if not os.getenv("DISPLAY"):
        raise SystemExit("DISPLAY is missing. Use run.sh to start the virtual display.")

    PROFILE.mkdir(parents=True, exist_ok=True)
    PROFILE.chmod(0o700)
    print("Starting isolated Chromium. Profile will stay on this VPS.", flush=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=False,
            locale="ru-RU",
            viewport=None,
            args=["--window-size=1320,740"],
            accept_downloads=False,
        )
        context.on("response", catalog_response)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(WB_URL, wait_until="domcontentloaded", timeout=45000)
            except (TimeoutError, Error) as error:
                print(
                    f"Initial navigation failed: {type(error).__name__}. "
                    "Check the browser window in noVNC.",
                    flush=True,
                )
            print("Browser ready; use the protected noVNC page for manual navigation.", flush=True)
            print("Test seller URL: https://www.wildberries.ru/seller/215484", flush=True)
            while True:
                pages = context.pages
                if not pages:
                    print("All browser tabs were closed.", flush=True)
                    return
                try:
                    pages[0].wait_for_timeout(2000)
                except Error:
                    time.sleep(0.3)
        except KeyboardInterrupt:
            pass
        finally:
            context.close()


if __name__ == "__main__":
    main()
