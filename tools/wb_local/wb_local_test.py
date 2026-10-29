#!/usr/bin/env python3
"""Local-only WB Playwright check: never uploads browser credentials."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl,urlencode,urlunsplit
import requests

CATALOG="/__internal/catalog/sellers/v4/catalog"
PROFILE=Path.home()/".wb-price-playwright-profile"

def is_catalog(url):
    p=urlsplit(url)
    return p.scheme=="https" and p.hostname=="www.wildberries.ru" and p.path==CATALOG

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seller",default="215484")
    ap.add_argument("--dest",default="1259571021")
    ap.add_argument("--brand",default="279103")
    ap.add_argument("--chrome",action="store_true")
    args=ap.parse_args()
    if not args.seller.isdecimal() or not args.brand.isdecimal() or not args.dest.lstrip("-").isdecimal():
        ap.error("Invalid seller, dest or brand")
    from playwright.sync_api import sync_playwright
    seen=[]
    def observed(req):
        if not is_catalog(req.url):
            return
        try:
            response=req.response()
            status=response.status if response else 0
            headers=req.all_headers()
            count=None
            if response and status==200:
                data=response.json()
                if isinstance(data,dict) and isinstance(data.get("products"),list):
                    count=len(data["products"])
            seen.append((req.url,headers,status))
            print("Browser catalog status:",status,"products:",count)
        except Exception as exc:
            print("Browser catalog observer:",type(exc).__name__)
    print("Separate browser opens; log into your account if necessary.")
    with sync_playwright() as pw:
        options=dict(user_data_dir=str(PROFILE),headless=False,locale="ru-RU")
        if args.chrome:
            options["channel"]="chrome"
        context=pw.chromium.launch_persistent_context(**options)
        context.on("requestfinished",observed)
        try:
            page=context.pages[0] if context.pages else context.new_page()
            page.goto("https://www.wildberries.ru/",wait_until="domcontentloaded",timeout=60000)
            input("Log in in the browser, then press Enter here: ")
            page.goto("https://www.wildberries.ru/seller/"+args.seller,wait_until="domcontentloaded",timeout=60000)
            page.wait_for_timeout(7000)
        finally:
            context.close()
    matching=[row for row in seen if row[2]==200]
    if not matching:
        print("No successful WB catalog request observed; no replay attempted.")
        return 2
    url,headers,_=matching[-1]
    query=dict(parse_qsl(urlsplit(url).query,keep_blank_values=True))
    query.update(supplier=args.seller,dest=args.dest,fbrand=args.brand,page="1")
    parsed=urlsplit(url)
    replay=urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(query),""))
    clean_headers={k:v for k,v in headers.items() if k.lower() not in
                   {"host","connection","content-length","accept-encoding","transfer-encoding"}}
    print("Observed Cookie:",bool(headers.get("cookie")),
          "Bearer:",bool(headers.get("authorization")))
    try:
        response=requests.get(replay,headers=clean_headers,timeout=(8,25),allow_redirects=False)
        print("Direct local GET status:",response.status_code)
        if response.status_code!=200:
            return 3
        data=response.json()
        if not isinstance(data,dict) or not isinstance(data.get("products"),list):
            print("Unexpected catalog response")
            return 4
        found=0
        for product in data["products"]:
            sizes=product.get("sizes") or []
            if not sizes or not isinstance(sizes[0],dict):
                continue
            price=(sizes[0].get("price") or {}).get("product")
            if price is None:
                continue
            found+=1
            if found<=5:
                print(product.get("id"),round(int(price)/100,2),"RUB",
                      str(product.get("name",""))[:60])
        print("Products with customer-facing prices:",found)
        return 0 if found else 4
    except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
        print("Local GET failed:",type(exc).__name__)
        return 5

if __name__=="__main__":
    import sys
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Cancelled")
        sys.exit(130)
