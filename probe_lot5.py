from playwright.sync_api import sync_playwright

URL = "https://rauch.de/en/fertiliser-spreaders/aero-gt/aero-gt-60-1.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables")
    for ti, t in enumerate(tables):
        print(f"\n--- TABLE {ti} ---")
        html = t.inner_html()
        print("LEN html:", len(html))
        rows = t.query_selector_all("tr")
        print(f"{len(rows)} rows")
        for ri, r in enumerate(rows[:25]):
            cells = r.query_selector_all("th, td")
            vals = [c.inner_text().strip().replace("\n", " ") for c in cells]
            print(f"  row {ri}: {vals}")
    browser.close()
