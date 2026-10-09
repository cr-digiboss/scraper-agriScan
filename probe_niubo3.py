from playwright.sync_api import sync_playwright

URLS = [
    "https://niubo.info/maquina/omega/",
    "https://niubo.info/maquina/ovni/",
    "https://niubo.info/maquina/shark/",
]


def dump(page, url):
    print(f"\n{'='*70}\n{url}\n{'='*70}")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        print("titre:", page.title())
        tables = page.query_selector_all("table")
        for i, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            if not rows:
                continue
            header0 = [c.inner_text().strip() for c in rows[0].query_selector_all("td, th")]
            if header0[:1] == ["Cookie"]:
                continue
            print(f"table {i}: {len(rows)} lignes")
            # dump raw html de la premiere ligne pour voir colspan eventuel
            print("  row0 html:", rows[0].inner_html()[:500])
            for r in rows[:8]:
                cells = [c.inner_text().strip() for c in r.query_selector_all("td, th")]
                print("  ", cells)
        # cherche aussi des listes/divs de caracteristiques (pas forcement une table)
        spec_divs = page.query_selector_all("[class*='caracteristic' i], [class*='ficha' i], [class*='spec' i]")
        print(f"{len(spec_divs)} divs spec-like")
        for d in spec_divs[:3]:
            txt = d.inner_text().strip().replace("\n", " | ")
            if txt:
                print("  echantillon:", txt[:300])
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for url in URLS:
        dump(page, url)
    browser.close()
