from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def inspect(page, url, label):
    print("\n" + "=" * 70)
    print(label, url)
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        print("titre:", page.title())
        tables = page.query_selector_all("table")
        print(f"{len(tables)} tables HTML")
        for t in tables[:3]:
            txt = t.inner_text().strip().replace("\n", " | ")
            print("  echantillon:", txt[:500])
        pdfs = page.eval_on_selector_all("a[href$='.pdf' i], a[href*='.pdf?' i]", "els => els.map(e => e.href)")
        print(f"{len(set(pdfs))} PDF:", sorted(set(pdfs))[:10])
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "landini-tractors.com/it/it" in h})
        print(f"{len(links)} sous-liens:")
        for l in links[:40]:
            print(" ", l)
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    inspect(page, "https://landini-tractors.com/it/it/prodotti/serie-5.html", "LANDINI serie-5")
    inspect(page, "https://landini-tractors.com/it/it/prodotti/rex4-cab.html", "LANDINI rex4-cab")
    inspect(page, "https://landini-tractors.com/it/it/prodotti/serie-6rs.html", "LANDINI serie-6rs")
    browser.close()
