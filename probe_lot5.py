import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright

BRANDS = {
    "amazone": {
        "home": "https://www.amazone.de/en/",
        "known": "https://www.amazone.de/en/products/mounted-sprayers/ux-5201-27201",
        "root": "amazone.de",
    },
    "lely": {
        "home": "https://www.lely.com/row/products/",
        "known": "https://www.lely.com/row/products/milking/vector/",
        "root": "lely.com",
    },
    "rauch": {
        "home": "https://rauch.de/en/fertiliser-spreader.html",
        "known": "https://rauch.de/en/fertiliser-spreaders/disc-spreader/axis-m.html",
        "root": "rauch.de",
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
            print("-- HOME --")
            page.goto(cfg["home"], timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print("titre:", page.title())
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if cfg["root"] in h})
            print(f"{len(links)} liens trouves sur le domaine")
            for l in links[:25]:
                print(" ", l)
        except Exception as e:
            print("ERREUR HOME:", e)

        try:
            print("\n-- FICHE CONNUE --")
            page.goto(cfg["known"], timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print("titre:", page.title())

            tables = page.query_selector_all("table")
            print(f"{len(tables)} tables HTML")
            for t in tables[:2]:
                txt = t.inner_text().strip().replace("\n", " | ")
                print("  echantillon table:", txt[:300])

            spec_divs = page.query_selector_all(
                "[class*='spec' i], [class*='technical' i], [class*='data' i], [class*='caracteristique' i]"
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
            print("ERREUR FICHE:", e)

        page.close()
    browser.close()
