from playwright.sync_api import sync_playwright

URLS = [
    "https://www.bednar.com/en/atlas-ae_profi/",
    "https://www.bednar.com/en/combination-cultivators/",
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
        print(f"{len(tables)} tables")
        for ti, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            print(f"\n--- TABLE {ti} ({len(rows)} rows) ---")
            for ri, r in enumerate(rows[:25]):
                cells = r.query_selector_all("th, td")
                vals = [c.inner_text().strip().replace("\n", " ")[:40] for c in cells]
                print(f"  row {ri}: {vals}")

        # liens produits sur la page categorie
        if "atlas" not in url:
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "bednar.com/en/" in h})
            import re
            produits = [l for l in links if re.search(r"/en/[a-z0-9_-]+/$", l) and l.count("/") == 4]
            print(f"\n{len(produits)} liens produits candidats (sous /en/):")
            for l in produits[:30]:
                print(" ", l)
    browser.close()
