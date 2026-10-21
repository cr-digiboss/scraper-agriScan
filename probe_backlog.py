from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    print("=" * 70)
    print("LANDINI home/produits")
    page.goto("https://www.landini.it/en/", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print("titre:", page.title())
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "landini.it" in h})
    print(f"{len(links)} liens landini.it:")
    for l in links[:60]:
        print(" ", l)

    browser.close()
