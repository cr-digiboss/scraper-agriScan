from playwright.sync_api import sync_playwright

URL = "https://www.vredo.com/en/products/agri-solutions/agricultural-overseeders/agri-air/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    print("titre:", page.title())

    body_text = page.inner_text("body")
    print("longueur body:", len(body_text))
    for kw in ["Technical", "Specifications", "Working width", "Weight", "kg", "Capacity"]:
        print(f"  contient {kw!r} ? {kw.lower() in body_text.lower()}")

    idx = body_text.lower().find("specif")
    if idx == -1:
        idx = body_text.lower().find("technical")
    print("\nextrait autour de 'specif'/'technical':")
    print(body_text[max(0, idx-100):idx+1500] if idx != -1 else "non trouve")

    print("\n--- 2000 premiers caracteres du body ---")
    print(body_text[:2000])
    browser.close()
