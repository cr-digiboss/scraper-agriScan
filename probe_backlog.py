import requests
import pdfplumber
from io import BytesIO
from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

print("=" * 70)
print("MERLO - recherche locale anglaise + structure complete des divs")
print("=" * 70)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    for url in [
        "https://www.merlo.com/eng/en/p/mezzi-speciali/dumper/dm/",
        "https://www.merlo.com/int/en/p/mezzi-speciali/dumper/dm/",
    ]:
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print(f"\n-- {url} --  titre:", page.title(), " url finale:", page.url)
        except Exception as e:
            print(f"-- {url} -- ERREUR:", e)

    page.goto("https://www.merlo.com/ita/it/p/mezzi-speciali/dumper/dm/", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    spec_divs = page.query_selector_all("[class*='spec' i], [class*='caracteristique' i], [class*='tecnich' i]")
    print(f"\n{len(spec_divs)} divs spec-like, contenu complet des 10 premiers:")
    for d in spec_divs[:10]:
        print("  -", d.inner_text().strip().replace("\n", " | ")[:200])

    # Cherche s'il y a plusieurs variantes/modeles (selecteur/tabs)
    variant_links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    variants = sorted({v for v in variant_links if "mezzi-speciali/dumper" in v})
    print(f"\n{len(variants)} liens variantes dumper:")
    for v in variants[:10]:
        print(" ", v)

    browser.close()

print("\n" + "=" * 70)
print("LANDINI - PDF brochure")
print("=" * 70)
url = "https://landini-tractors.com/content/dam/landini/gb/products/rs2b-serie-5/LA_RS57-RS2B_Serie5_Brochure_52p_6697627A2_Web_EN.pdf.inline.pdf"
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
