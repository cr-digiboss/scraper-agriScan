import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright

BRANDS = {
    "amazone": {
        "cat": "https://amazone.de/en-en/products",
        "root": "amazone.de",
        "product_hint": "/products/",
    },
    "lely": {
        "cat": "https://www.lely.com/global/products/",
        "root": "lely.com",
        "product_hint": "/products/",
    },
    "rauch": {
        "cat": "https://rauch.de/en/fertiliser-spreaders/disc-spreader.html",
        "root": "rauch.de",
        "product_hint": "/fertiliser-spreaders/",
    },
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    for brand, cfg in BRANDS.items():
        print("\n" + "=" * 70)
        print(f"MARQUE: {brand}")
        print("=" * 70)
        page = browser.new_page()
        try:
            print("-- CATEGORIE --")
            page.goto(cfg["cat"], timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print("titre:", page.title())
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if cfg["root"] in h})
            produits = [l for l in links if cfg["product_hint"] in l and l.rstrip('/') != cfg["cat"].rstrip('/')]
            print(f"{len(produits)} liens produits candidats:")
            for l in produits[:15]:
                print(" ", l)

            if not produits:
                page.close()
                continue

            known = produits[0]
            print(f"\n-- FICHE: {known} --")
            page.goto(known, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print("titre:", page.title())

            tables = page.query_selector_all("table")
            print(f"{len(tables)} tables HTML")
            for t in tables[:3]:
                txt = t.inner_text().strip().replace("\n", " | ")
                print("  echantillon table:", txt[:400])

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
            pdfs_uniq = sorted(set(pdfs))
            print(f"{len(pdfs_uniq)} PDF uniques trouves:")
            for pu in pdfs_uniq[:10]:
                print("  ", pu)

            if pdfs_uniq:
                url = pdfs_uniq[0]
                print(f"\n  Analyse PDF: {url}")
                try:
                    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                    resp.raise_for_status()
                    with pdfplumber.open(BytesIO(resp.content)) as pdf:
                        print(f"  {len(pdf.pages)} pages")
                        for pi, pg in enumerate(pdf.pages[:8]):
                            tbls = pg.extract_tables()
                            txt_sample = (pg.extract_text() or "")[:150]
                            print(f"  page {pi}: {len(tbls)} table(s), texte: {txt_sample!r}")
                            for ti, t in enumerate(tbls):
                                print(f"    table {ti}: {len(t)} lignes")
                                for row in t[:6]:
                                    print("     ", row)
                except Exception as e:
                    print("  ERREUR PDF:", e)
        except Exception as e:
            print("ERREUR:", e)

        page.close()
    browser.close()
