import requests
import re
from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

BLOCKLIST_EXACT = {
    "2wd-tractors", "4wd-tractors", "latest-tractors", "accessories",
    "tractor-pricelist", "digisense", "compact-tractors", "oja-tractors",
    "novo-tractors", "jivo-tractors", "yuvraj-tractors", "xp-tractors",
    "sp-tractors", "arjun-tractors",
}

r = requests.get("https://www.mahindratractor.com/english-sitemap.xml", timeout=20, headers={"User-Agent": UA})
urls = re.findall(r"<loc>(.*?)</loc>", r.text)
tractors_urls = sorted({u for u in urls if "/tractors/" in u})
print(f"{len(tractors_urls)} URLs /tractors/ au total")

candidates = []
for u in tractors_urls:
    slug = u.rstrip("/").split("/")[-1]
    if slug in BLOCKLIST_EXACT:
        continue
    if re.search(r"-hp-tractors$|-kw-\d+-hp-to-\d+-hp-tractors$|^\d+-to-\d+", slug):
        continue
    if slug.endswith("-tractors") or slug.endswith("-tractor-list"):
        continue
    candidates.append(u)

print(f"\n{len(candidates)} candidats produits apres filtre:")
for c in candidates:
    print(" ", c)

# Valide la structure de table sur un echantillon
sample = candidates[:4]
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    for url in sample:
        print("\n" + "=" * 70)
        print(url)
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            print("titre:", page.title())
            tables = page.query_selector_all("table")
            print(f"{len(tables)} tables")
            for ti, t in enumerate(tables[:2]):
                rows = t.query_selector_all("tr")
                print(f"--- table {ti} ({len(rows)} rows) ---")
                for ri, row in enumerate(rows[:10]):
                    cells = row.query_selector_all("th, td")
                    vals = [c.inner_text().strip().replace("\n", " ")[:40] for c in cells]
                    print(f"  row {ri}: {vals}")
        except Exception as e:
            print("ERREUR:", e)
    browser.close()
