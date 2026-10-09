from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

HOME = "https://agrisem.com/"
SAMPLE_PRODUCTS = [
    "https://agrisem.com/product/t-boss/",
    "https://agrisem.com/product/semoir-en-ligne-vibrosem/",
    "https://agrisem.com/product/boss-porte-monorampe/",
]


def dump_page(page, label, url):
    print(f"\n{'='*80}\n{label} — {url}\n{'='*80}")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        print("Titre:", page.title())
        tables = page.query_selector_all("table")
        print(f"{len(tables)} tables")
        for i, t in enumerate(tables[:5]):
            rows = t.query_selector_all("tr")
            print(f"  table {i}: {len(rows)} lignes")
            for r in rows[:6]:
                cells = [c.inner_text().strip() for c in r.query_selector_all("td, th")]
                print(f"    {cells}")
        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], "
            "[class*='fiche-technique' i]"
        )
        print(f"{len(spec_divs)} divs spec-like")
        for d in spec_divs[:3]:
            txt = d.inner_text().strip().replace("\n", " | ")
            if txt:
                print("  echantillon:", txt[:400])
        pdfs = page.eval_on_selector_all("a[href*='.pdf' i]", "els => els.map(e => e.href)")
        print(f"{len(pdfs)} PDF")
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    dump_page(page, "Agrisem home", HOME)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    product_links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if '/product/' in urlparse(h).path})
    print(f"\n{len(product_links)} liens /product/ trouves sur la home:")
    for l in product_links[:20]:
        print(" ", l)

    for url in SAMPLE_PRODUCTS:
        dump_page(page, "Agrisem produit", url)

    browser.close()
