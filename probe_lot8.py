from playwright.sync_api import sync_playwright

BRANDS = {
    "landini": "https://www.landini.it/en/",
    "merlo": "https://www.merlo.com/en/int/",
    "pellenc": "https://www.pellenc.com/en/",
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    for brand, home in BRANDS.items():
        print("\n" + "=" * 70)
        print(f"MARQUE: {brand}")
        print("=" * 70)
        page = browser.new_page()
        try:
            page.goto(home, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            print("titre:", page.title())
            print("url finale:", page.url)
            root = page.url.split("//")[1].split("/")[0].replace("www.", "")
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if root in h})
            print(f"{len(links)} liens trouves sur le domaine")
            for l in links[:40]:
                print(" ", l)
        except Exception as e:
            print("ERREUR:", e)
        page.close()
    browser.close()
