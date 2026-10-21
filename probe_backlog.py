from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    print("=" * 70)
    print("LANDINI home")
    page.goto("https://www.landini.it/en/", timeout=25000, wait_until="networkidle")
    page.wait_for_timeout(5000)
    print("titre:", page.title())
    print("url finale:", page.url)
    html = page.content()
    print("longueur HTML:", len(html))
    print("extrait body:", html[html.find("<body"):html.find("<body") + 1500])

    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    print(f"\n{len(hrefs)} liens <a> bruts (avant filtre)")
    for h in hrefs[:40]:
        print(" ", h)

    browser.close()
