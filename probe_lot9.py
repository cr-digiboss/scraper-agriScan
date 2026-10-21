from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def inspect(page, url, label):
    print("\n" + "=" * 70)
    print(label, url)
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        print("ERREUR goto:", e)
        return
    print("titre:", page.title())
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables HTML")
    for t in tables[:3]:
        txt = t.inner_text().strip().replace("\n", " | ")
        print("  echantillon:", txt[:400])
    spec_divs = page.query_selector_all(
        "[class*='spec' i], [class*='technical' i], [class*='data-table' i]"
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

    # liste liens produits si page categorie
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = sorted(set(hrefs))
    return links


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    # STEYR
    links = inspect(page, "https://www.steyr-traktoren.com/en/agriculture/products/tractors/terrus-cvt", "STEYR categorie")
    if links:
        cand = [l for l in links if "terrus-cvt" in l and l.count("/") > 7]
        print("liens produits candidats:", cand[:20])

    # DEUTZ-FAHR
    links = inspect(page, "https://www.deutz-fahr.com/en-nd/tractors/5-series", "DEUTZ-FAHR categorie")
    if links:
        cand = [l for l in links if "deutz-fahr.com" in l and "5-series" in l]
        print("liens produits candidats:", cand[:20])

    # MANITOU
    inspect(page, "https://www.manitou.com/en-GB", "MANITOU home en-GB")

    browser.close()
