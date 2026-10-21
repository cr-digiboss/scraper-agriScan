from playwright.sync_api import sync_playwright

URLS = [
    "https://www.pellenc.com/en-gb/our-products/from-the-vineyard-to-the-winery/vine-growing/battery-power-tools/f3x-tying-machine",
    "https://www.pellenc.com/en-gb/our-products/from-the-vineyard-to-the-winery/vine-growing/battery-power-tools/fixion-2-tying-machine",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for url in URLS:
        print("\n" + "=" * 70)
        print(url)
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        print("titre:", page.title())
        tables = page.query_selector_all("table")
        print(f"{len(tables)} tables HTML")
        for t in tables[:3]:
            txt = t.inner_text().strip().replace("\n", " | ")
            print("  echantillon:", txt[:400])
        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='characteristic' i]"
        )
        print(f"{len(spec_divs)} divs spec-like")
        for d in spec_divs[:3]:
            txt = d.inner_text().strip().replace("\n", " | ")
            if txt:
                print("  echantillon div:", txt[:400])
        pdfs = page.eval_on_selector_all(
            "a[href$='.pdf' i], a[href*='.pdf?' i]", "els => els.map(e => e.href)"
        )
        print(f"{len(set(pdfs))} PDF uniques:", sorted(set(pdfs))[:5])
    browser.close()
