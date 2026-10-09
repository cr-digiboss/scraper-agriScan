from playwright.sync_api import sync_playwright

URLS = [
    "https://rauch.de/en/fertiliser-spreaders/disc-spreader/axis-h/axis-h-30-2-emc-w.html",
    "https://rauch.de/en/fertiliser-spreaders/disc-spreader/mds/mds-14-2.html",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for url in URLS:
        print("\n" + "=" * 70)
        print(url)
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        tables = page.query_selector_all("table")
        print(f"{len(tables)} tables")
        for ti, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            print(f"\n--- TABLE {ti} ({len(rows)} rows) ---")
            for ri, r in enumerate(rows[:25]):
                cells = r.query_selector_all("th, td")
                vals = [c.inner_text().strip().replace("\n", " ")[:40] for c in cells]
                print(f"  row {ri}: {vals}")
    browser.close()
