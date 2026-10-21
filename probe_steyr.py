from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

URL = "https://www.steyr-traktoren.com/en/agriculture/products/tractors/terrus-cvt"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    print("titre:", page.title())

    body_text = page.inner_text("body")
    print("longueur body:", len(body_text))

    idx = body_text.lower().find("max engine power")
    print("\nextrait autour de 'max engine power':")
    print(body_text[max(0, idx - 500): idx + 2500])

    # Cherche des boutons/tabs de modeles (ex. CVT 6300, 6280...)
    tabs = page.query_selector_all("[role='tab'], button, [class*='tab' i], [class*='model' i]")
    print(f"\n{len(tabs)} elements tab/button/model-like")
    labels = []
    for el in tabs[:60]:
        t = el.inner_text().strip()
        if t and len(t) < 60:
            labels.append(t)
    print("libelles:", labels[:60])

    browser.close()
