import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright

URLS = [
    "https://www.vredo.com/en/products/agri-solutions/agricultural-overseeders/agri-air/",
    "https://www.vredo.com/en/products/agri-solutions/slurry-application-for-maximum-results/profi-xl/",
    "https://www.vredo.com/en/products/agri-solutions/slurry-injection/self-propelled-tracs/",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for url in URLS:
        print("\n" + "=" * 70)
        print(url)
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        print("titre:", page.title())
        tables = page.query_selector_all("table")
        print(f"{len(tables)} tables HTML")
        for t in tables[:3]:
            txt = t.inner_text().strip().replace("\n", " | ")
            print("  echantillon:", txt[:400])

        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='data-table' i]"
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
        print(f"{len(pdfs_uniq)} PDF uniques:")
        for pu in pdfs_uniq[:10]:
            print("  ", pu)

        if pdfs_uniq:
            url_pdf = pdfs_uniq[0]
            try:
                resp = requests.get(url_pdf, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                with pdfplumber.open(BytesIO(resp.content)) as pdf:
                    print(f"  PDF {len(pdf.pages)} pages")
                    for pi, pg in enumerate(pdf.pages[:6]):
                        tbls = pg.extract_tables()
                        print(f"  page {pi}: {len(tbls)} table(s), texte: {(pg.extract_text() or '')[:150]!r}")
                        for ti, t in enumerate(tbls):
                            print(f"    table {ti}: {len(t)} lignes, ex: {t[:3]}")
            except Exception as e:
                print("  ERREUR PDF:", e)
    browser.close()
