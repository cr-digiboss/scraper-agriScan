from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

URLS = [
    "https://www.mahindratractor.com/tractor/arjun-555-di",
    "https://www.mahindratractor.com/tractor/arjun-605-di-pp",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
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
            for ri, r in enumerate(rows[:35]):
                cells = r.query_selector_all("th, td")
                vals = [c.inner_text().strip().replace("\n", " ")[:50] for c in cells]
                print(f"  row {ri}: {vals}")

        # Cherche aussi tous les liens produits sur une page listant TOUS les tracteurs
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "mahindratractor.com/tractor/" in h})
        print(f"\n{len(links)} liens /tractor/ sur cette page:")
        for l in links[:40]:
            print(" ", l)
    browser.close()
