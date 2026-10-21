import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

print("=" * 70)
print("DEUTZ-FAHR PDF")
print("=" * 70)
url = "https://www.deutz-fahr.com/media/308.8901.3.4-1_Serie_5_Stage_V_EN.pdf"
resp = requests.get(url, timeout=30, headers={"User-Agent": UA})
print("status:", resp.status_code, "bytes:", len(resp.content))
with pdfplumber.open(BytesIO(resp.content)) as pdf:
    print(f"{len(pdf.pages)} pages")
    for pi, pg in enumerate(pdf.pages):
        tbls = pg.extract_tables()
        if tbls:
            print(f"page {pi}: {len(tbls)} table(s), texte: {(pg.extract_text() or '')[:100]!r}")
            for ti, t in enumerate(tbls):
                print(f"  table {ti}: {len(t)} lignes, ex: {t[:4]}")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    print("\n" + "=" * 70)
    print("STEYR - liens sur la page Terrus CVT (tous, pour trouver variantes)")
    print("=" * 70)
    page.goto("https://www.steyr-traktoren.com/en/agriculture/products/tractors/terrus-cvt", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "steyr-traktoren.com" in h and "terrus" in h.lower()})
    print(f"{len(links)} liens contenant 'terrus':")
    for l in links:
        print(" ", l)

    # Cherche un selecteur de modele (dropdown/boutons)
    selects = page.query_selector_all("select, [class*='model-select' i], [class*='variant' i]")
    print(f"\n{len(selects)} elements select/variant-like")

    print("\n" + "=" * 70)
    print("MANITOU - page produits")
    print("=" * 70)
    for url2 in [
        "https://www.manitou.com/en-GB/products",
        "https://www.manitou.com/en-GB/range",
    ]:
        try:
            page.goto(url2, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print(f"\n-- {url2} --  titre:", page.title(), " url finale:", page.url)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "manitou.com" in h})
            print(f"{len(links)} liens:")
            for l in links[:25]:
                print(" ", l)
        except Exception as e:
            print(f"-- {url2} -- ERREUR:", e)

    browser.close()
