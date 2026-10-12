from playwright.sync_api import sync_playwright

URL = "https://info.amazone.de/displayprospekt.aspx?sprache=1&drucknummer=P0023&path=99*92&display=infoPages&page=24"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    resp = page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    print("status:", resp.status if resp else None)
    print("url finale:", page.url)
    page.wait_for_timeout(3000)
    print("titre:", page.title())
    body_text = page.inner_text("body")
    print("longueur body:", len(body_text))
    print(body_text[:1000])

    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables")

    # Cherche un lien PDF embarque
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    pdfs = [h for h in hrefs if ".pdf" in h.lower()]
    print("PDF links:", pdfs[:10])

    iframes = page.query_selector_all("iframe")
    print(f"{len(iframes)} iframes")
    for f in iframes[:5]:
        print(" src:", f.get_attribute("src"))

    browser.close()
