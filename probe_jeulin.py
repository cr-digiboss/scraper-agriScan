import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

HOME = "https://jeulinsa.fr/"
KNOWN_PAGE = "https://jeulinsa.fr/machine/tornado-560-2/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    print("="*70, "\nHOME\n", "="*70)
    page.goto(HOME, timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print("titre:", page.title())
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    root = "jeulinsa.fr"
    links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if root in h})
    print(f"{len(links)} liens trouves")
    produits = [l for l in links if "/machine/" in l]
    print(f"{len(produits)} liens /machine/:")
    for l in produits[:40]:
        print(" ", l)

    print("\n", "="*70, "\nPDF de la fiche connue\n", "="*70)
    page.goto(KNOWN_PAGE, timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    pdfs = page.eval_on_selector_all("a[href$='.pdf' i]", "els => els.map(e => e.href)")
    pdfs_uniq = sorted(set(pdfs))
    print(f"{len(pdfs_uniq)} PDF uniques:")
    for pu in pdfs_uniq:
        print(" ", pu)

    # verifie aussi s'il y a une table HTML ou des divs specs
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables HTML")
    spec_divs = page.query_selector_all("[class*='spec' i], [class*='caracteristique' i], [class*='technique' i]")
    print(f"{len(spec_divs)} divs spec-like")
    for d in spec_divs[:3]:
        txt = d.inner_text().strip().replace("\n", " | ")
        if txt:
            print("  echantillon:", txt[:300])

    browser.close()

if pdfs_uniq:
    url = pdfs_uniq[0]
    print("\n", "="*70, f"\nContenu PDF: {url}\n", "="*70)
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        print(f"{len(pdf.pages)} pages")
        for pi, pg in enumerate(pdf.pages):
            tables = pg.extract_tables()
            text_sample = (pg.extract_text() or "")[:150]
            print(f"page {pi}: {len(tables)} tables, texte: {text_sample!r}")
            for ti, t in enumerate(tables):
                print(f"  table {ti}: {len(t)} lignes")
                for row in t[:8]:
                    print("   ", row)
