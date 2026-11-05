from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA, viewport={"width": 1366, "height": 900})
    page.goto("https://www.weidemann.de/produkte/hoflader/hoftrac-1160", timeout=25000, wait_until="networkidle")
    page.wait_for_timeout(3000)
    for _ in range(6):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(1000)

    html = page.content()
    print("longueur HTML:", len(html))
    idx = html.lower().find("technisch")
    print("index 'technisch':", idx)
    if idx >= 0:
        print(html[max(0, idx - 200):idx + 2000])

    # Chercher accordions/tabs
    accordions = page.query_selector_all("[class*='accordion' i], [class*='tab' i], button")
    print(f"\n{len(accordions)} elements accordion/tab/button")
    for el in accordions[:15]:
        try:
            txt = el.inner_text().strip()[:60]
            if txt:
                print("  ", txt)
        except Exception:
            pass

    browser.close()
