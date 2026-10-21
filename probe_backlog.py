import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

PRODUCTS = {
    "tecnoma": "https://www.tecnoma.com/en/products/sprayers-for-agriculture/self-propelled-sprayers/",
    "gregoire-besson": "https://www.gregoire-besson.com/en/machines/discordon",
    "landini": "https://landini-tractors.com/gb/en/products/serie-5.html",
    "merlo": "https://www.merlo.com/ita/it/p/mezzi-speciali/dumper/dm/",
}


def inspect(page, url, label):
    print("\n" + "=" * 70)
    print(label, url)
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    print("titre:", page.title())
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables HTML")
    for t in tables[:3]:
        txt = t.inner_text().strip().replace("\n", " | ")
        print("  echantillon:", txt[:400])
    spec_divs = page.query_selector_all(
        "[class*='spec' i], [class*='technical' i], [class*='data-table' i], [class*='caracteristique' i]"
    )
    print(f"{len(spec_divs)} divs spec-like")
    for d in spec_divs[:3]:
        txt = d.inner_text().strip().replace("\n", " | ")
        if txt:
            print("  echantillon div:", txt[:400])
    pdfs = page.eval_on_selector_all(
        "a[href$='.pdf' i], a[href*='.pdf?' i]", "els => els.map(e => e.href)"
    )
    print(f"{len(set(pdfs))} PDF uniques:", sorted(set(pdfs))[:5])
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    return sorted(set(hrefs))


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    for brand, url in PRODUCTS.items():
        links = inspect(page, url, brand.upper())
    browser.close()
