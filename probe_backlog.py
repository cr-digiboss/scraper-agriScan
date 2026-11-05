from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    page.goto(
        "https://www.weidemann.de/produkte/hoflader/hoftrac-1160/technische-daten/tab",
        timeout=25000, wait_until="domcontentloaded",
    )
    page.wait_for_timeout(3000)
    print("titre:", page.title())
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables HTML")
    for ti, t in enumerate(tables):
        txt = t.inner_text().strip().replace("\n", " | ")
        print(f"  table {ti}:", txt[:600])

    tech = page.query_selector_all("[class*='tech' i], [class*='spec' i], [class*='data' i], dl")
    print(f"\n{len(tech)} elements tech/spec/data-like")
    for el in tech[:5]:
        try:
            txt = el.inner_text().strip().replace("\n", " | ")
            if txt and len(txt) > 20:
                print("  tech:", txt[:800])
        except Exception:
            pass

    browser.close()
