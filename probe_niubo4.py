from playwright.sync_api import sync_playwright

URL = "https://niubo.info/maquina/omega/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    tables = page.query_selector_all("table")
    for t in tables:
        rows = t.query_selector_all("tr")
        if not rows:
            continue
        header0 = [c.inner_text().strip() for c in rows[0].query_selector_all("td, th")]
        if header0[:1] == ["Cookie"]:
            continue
        imgs = rows[0].query_selector_all("img")
        print(f"{len(imgs)} icones en ligne 0:")
        for img in imgs:
            print(" ", img.get_attribute("src"), "| alt=", img.get_attribute("alt"), "| title=", img.get_attribute("title"))
    browser.close()
