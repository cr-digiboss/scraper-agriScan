import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

URL = "https://www.steyr-traktoren.com/en/agriculture/products/tractors/terrus-cvt"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    all_links = page.eval_on_selector_all(
        "a", "els => els.map(e => ({href: e.getAttribute('href'), text: (e.textContent||'').trim().slice(0,50)}))"
    )
    pdf_like = [l for l in all_links if l.get('href') and '.pdf' in l['href'].lower()]
    brochure_like = [l for l in all_links if 'brochure' in (l.get('text') or '').lower()]
    print("liens pdf:", pdf_like)
    print("liens brochure (texte):", brochure_like)

    browser.close()

pdf_url = None
if pdf_like:
    pdf_url = pdf_like[0]['href']
elif brochure_like and brochure_like[0].get('href'):
    pdf_url = brochure_like[0]['href']

if pdf_url:
    if not pdf_url.startswith("http"):
        pdf_url = "https://www.steyr-traktoren.com" + pdf_url
    print(f"\nTelechargement: {pdf_url}")
    resp = requests.get(pdf_url, timeout=30, headers={"User-Agent": UA})
    print("status:", resp.status_code, "bytes:", len(resp.content))
    if resp.status_code == 200:
        with pdfplumber.open(BytesIO(resp.content)) as pdf:
            print(f"{len(pdf.pages)} pages")
            for pi, pg in enumerate(pdf.pages):
                tbls = pg.extract_tables()
                if tbls:
                    print(f"page {pi}: {len(tbls)} table(s), texte: {(pg.extract_text() or '')[:100]!r}")
                    for ti, t in enumerate(tbls):
                        print(f"  table {ti}: {len(t)} lignes, ex: {t[:4]}")
else:
    print("Aucun lien PDF/brochure trouve")
