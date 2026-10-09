from playwright.sync_api import sync_playwright

PAGES = {
    "Niubo home": "https://niubo.info/",
    "Einbock Vibrostar (PDF check)": "https://www.einboeck.at/produkte/bodenbearbeitung/feingrubber/vibrostar/",
    "Geringhoff North Star": "https://www.geringhoff.com/en_US/Products/Corn-Heads/North-Star-/p/gp_MaisStar",
    "Jeulin Tornado 560": "https://jeulinsa.fr/machine/tornado-560-2/",
}


def dump(page, label, url):
    print(f"\n{'='*70}\n{label} — {url}\n{'='*70}")
    try:
        resp = page.goto(url, timeout=25000, wait_until="domcontentloaded")
        print("status:", resp.status if resp else None)
        page.wait_for_timeout(3000)
        print("titre:", page.title())
        print("url finale:", page.url)
        pdfs = page.eval_on_selector_all("a[href$='.pdf' i], a[href*='.pdf?' i]", "els => els.map(e => e.href)")
        print(f"{len(pdfs)} PDF:")
        for p in pdfs[:5]:
            print("  ", p)
        tables = page.query_selector_all("table")
        print(f"{len(tables)} tables")
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for label, url in PAGES.items():
        dump(page, label, url)
    browser.close()
