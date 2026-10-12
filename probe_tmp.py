import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright
import scraper

URLS = [
    "https://amazone.net/en/products-digital-solutions/agricultural-technology/fertilising-technology/mounted-spreader/za-ts-mounted-spreader-51506",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for url in URLS:
        print("\n" + "=" * 70)
        print(url)
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        params = scraper._amazone_find_leaflet_params(page)
        print("params:", params)
        drucknummer, page_num = params
        resp = requests.get(
            f"https://downloadcenter.amazone.de/file/view/printnumber/{drucknummer}/language/en-gb/doctype/leaflet",
            params={"page": page_num},
            headers={"User-Agent": "Mozilla/5.0", "Referer": url},
            timeout=30,
        )
        with pdfplumber.open(BytesIO(resp.content)) as pdf:
            print(f"{len(pdf.pages)} pages")
            pg = pdf.pages[0]
            tables = pg.extract_tables()
            print(f"{len(tables)} tables sur la page")
            for ti, t in enumerate(tables):
                print(f"\n--- TABLE {ti} ({len(t)} lignes) ---")
                for ri, row in enumerate(t[:25]):
                    print(f"  row {ri}: {row}")

            print("\n--- TEXTE BRUT COMPLET ---")
            text = pg.extract_text() or ""
            for i, line in enumerate(text.split("\n")):
                print(f"  L{i}: {line!r}")
    browser.close()
