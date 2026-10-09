import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

HOME = "https://www.geringhoff.com/en_US/Products"
KNOWN_PAGE = "https://www.geringhoff.com/en_US/Products/Corn-Heads/North-Star-/p/gp_MaisStar"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    print("="*70, "\nHOME\n", "="*70)
    page.goto(HOME, timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print("titre:", page.title())
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    root = "geringhoff.com"
    links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if root in h})
    print(f"{len(links)} liens trouves")
    produits = [l for l in links if "/Products/" in l]
    print(f"{len(produits)} liens sous /Products/:")
    for l in produits[:40]:
        print(" ", l)

    print("\n", "="*70, "\nPDF de la fiche connue\n", "="*70)
    page.goto(KNOWN_PAGE, timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    pdfs = page.eval_on_selector_all("a[href$='.pdf' i], a[href*='.pdf?' i]", "els => els.map(e => e.href)")
    pdfs_uniq = sorted(set(pdfs))
    print(f"{len(pdfs_uniq)} PDF uniques:")
    for pu in pdfs_uniq:
        print(" ", pu)

    browser.close()

if pdfs_uniq:
    url = pdfs_uniq[0]
    print("\n", "="*70, f"\nContenu PDF: {url}\n", "="*70)
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        print(f"{len(pdf.pages)} pages")
        for pi, pg in enumerate(pdf.pages[:6]):
            tables = pg.extract_tables()
            print(f"page {pi}: {len(tables)} tables, texte(200 premiers car): {(pg.extract_text() or '')[:200]!r}")
            for ti, t in enumerate(tables):
                print(f"  table {ti}: {len(t)} lignes")
                for row in t[:8]:
                    print("   ", row)
