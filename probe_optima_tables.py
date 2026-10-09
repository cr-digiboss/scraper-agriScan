from playwright.sync_api import sync_playwright

URL = "https://ien.kverneland.com/seeders/pneumatic-precision-drills/optima-r"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables trouvees")
    for ti, table in enumerate(tables):
        rows = table.query_selector_all("tr")
        print(f"--- table {ti} : {len(rows)} lignes ---")
        for ri, row in enumerate(rows[:6]):
            cells = [c.inner_text().strip() for c in row.query_selector_all("td, th")]
            print(f"  row {ri}: {cells}")
    browser.close()
