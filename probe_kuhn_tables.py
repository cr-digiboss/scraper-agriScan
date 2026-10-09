from playwright.sync_api import sync_playwright

URL = "https://www.kuhn.fr/grande-culture/pulverisateurs/pulverisateurs-automoteurs"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    for _ in range(6):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(250)
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables trouvees")
    print("title:", page.title())
    for ti, table in enumerate(tables):
        rows = table.query_selector_all("tr")
        print(f"--- table {ti} : {len(rows)} lignes ---")
        for ri, row in enumerate(rows[:5]):
            cells = [c.inner_text().strip() for c in row.query_selector_all("td, th")]
            print(f"  row {ri}: {cells}")
    browser.close()
