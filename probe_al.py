import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright

AMAZONE_CATEGORY = "https://amazone.net/en/products-digital-solutions/agricultural-technology/fertilising-technology/mounted-spreader"
LELY_PRODUCT = "https://www.lely.com/solutions/milking/astronaut/"


def inspect(page, url, label):
    print("\n" + "=" * 70)
    print(label, url)
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print("titre:", page.title())
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables HTML")
    for t in tables[:3]:
        txt = t.inner_text().strip().replace("\n", " | ")
        print("  echantillon:", txt[:300])
    spec_divs = page.query_selector_all(
        "[class*='spec' i], [class*='technical' i], [class*='data-table' i]"
    )
    print(f"{len(spec_divs)} divs spec-like")
    for d in spec_divs[:3]:
        txt = d.inner_text().strip().replace("\n", " | ")
        if txt:
            print("  echantillon div:", txt[:300])
    pdfs = page.eval_on_selector_all(
        "a[href$='.pdf' i], a[href*='.pdf?' i]", "els => els.map(e => e.href)"
    )
    pdfs_uniq = sorted(set(pdfs))
    print(f"{len(pdfs_uniq)} PDF uniques:")
    for pu in pdfs_uniq[:10]:
        print("  ", pu)
    return pdfs_uniq


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    print("=" * 70)
    print("AMAZONE - page categorie (pour trouver des liens produits concrets)")
    print("=" * 70)
    page.goto(AMAZONE_CATEGORY, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "amazone.net" in h})
    # Les vraies fiches produit ont un ID numerique en fin de slug
    import re
    produits = [l for l in links if re.search(r"-\d{5,}$", l)]
    print(f"{len(produits)} liens produits (avec ID numerique):")
    for l in produits[:20]:
        print(" ", l)

    if produits:
        inspect(page, produits[0], "AMAZONE PRODUIT")

    inspect(page, LELY_PRODUCT, "LELY PRODUIT")

    browser.close()
