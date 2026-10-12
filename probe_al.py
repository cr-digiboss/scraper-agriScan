from playwright.sync_api import sync_playwright

AMAZONE_PRODUCT = "https://amazone.net/en/products-digital-solutions/agricultural-technology/fertilising-technology/mounted-spreader/za-m-mounted-spreader-51846"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(AMAZONE_PRODUCT, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    body_text = page.inner_text("body")
    idx = body_text.find("Technical data")
    print("longueur totale:", len(body_text))
    print("extrait autour de 'Technical data':")
    print(body_text[max(0, idx - 200): idx + 1500])

    # html brut autour du mot pour voir la structure
    html = page.content()
    idx2 = html.find("Technical data")
    print("\n\nHTML brut (2000 car. apres le mot) :")
    print(html[idx2: idx2 + 2000])
    browser.close()
