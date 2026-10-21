import requests
from io import BytesIO
import pdfplumber
from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def inspect_pdf(url, label):
    print("\n" + "=" * 70)
    print(label, url)
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": UA})
        print("status:", r.status_code, "bytes:", len(r.content))
        with pdfplumber.open(BytesIO(r.content)) as pdf:
            print(f"{len(pdf.pages)} pages")
            for pi, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    for ti, t in enumerate(tables):
                        print(f"  page {pi} table {ti}: {len(t)} rows x {len(t[0]) if t else 0} cols")
                        for row in t[:5]:
                            print("    ", row)
    except Exception as e:
        print("ERREUR:", e)


inspect_pdf("https://www.tecnoma.fr/wp-content/uploads/2023/TECNOMA_Brochure-LASER-2.pdf", "TECNOMA brochure")

# Gregoire Besson : chercher des specs sous forme JS/accordion
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    print("\n" + "=" * 70)
    print("GREGOIRE BESSON - recherche produit")
    try:
        page.goto("https://www.gregoire-besson.com/en/", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "gregoire-besson.com" in h})
        print(f"{len(links)} liens trouves (echantillon):")
        for l in links[:30]:
            print(" ", l)
    except Exception as e:
        print("ERREUR:", e)
    browser.close()
