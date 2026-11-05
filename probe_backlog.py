from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    # WEIDEMANN : structure exacte des tables sur la sous-page technische-daten
    page.goto("https://www.weidemann.de/produkte/hoflader/hoftrac-1160/technische-daten/tab", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print("=" * 70)
    print("WEIDEMANN - structure tables (via query_selector)")
    tables = page.query_selector_all("table")
    for ti, t in enumerate(tables[:3]):
        rows = t.query_selector_all("tr")
        print(f"table {ti} ({len(rows)} rows):")
        for r in rows[:6]:
            cells = r.query_selector_all("td, th")
            vals = [c.inner_text().strip() for c in cells]
            print("   ", vals)

    print("\ntitre complet:", page.title())

    # SCHAFFER : structure exacte du bloc technical data
    page2 = browser.new_page(user_agent=UA)
    page2.goto("https://www.schaeffer.de/en/products/10/compact-loader-4670", timeout=25000, wait_until="domcontentloaded")
    page2.wait_for_timeout(3000)
    print("\n" + "=" * 70)
    print("SCHAFFER - recherche conteneur technical data")
    # Chercher le heading "Technical data" et son parent
    heading = page2.query_selector("text=Technical data")
    if heading:
        parent = heading.evaluate_handle("el => el.closest('section') || el.parentElement.parentElement")
        html = parent.evaluate("el => el.outerHTML")
        print("HTML parent (1500 premiers car):")
        print(html[:1500])
    else:
        print("heading 'Technical data' non trouve")

    browser.close()
