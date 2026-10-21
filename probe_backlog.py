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
        print("url finale:", page.url)
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
            try:
                txt = d.inner_text().strip().replace("\n", " | ")
                if txt:
                    print("  echantillon div:", txt[:400])
            except Exception:
                pass
        pdfs = page.eval_on_selector_all(
            "a[href$='.pdf' i], a[href*='.pdf?' i]", "els => els.map(e => e.href)"
        )
        print(f"{len(set(pdfs))} PDF uniques:", sorted(set(pdfs))[:5])
        if url.rstrip("/").endswith("tractors"):
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "mahindratractor.com/tractor/" in h})
            print(f"{len(links)} liens produits /tractor/:")
            for l in links[:30]:
                print(" ", l)
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    inspect(page, "https://www.mahindratractor.com/tractors", "MAHINDRA categorie")
    inspect(page, "https://www.mahindratractor.com/tractor/arjun-555-di", "MAHINDRA produit")

    page2 = browser.new_page(user_agent=UA)
    inspect(page2, "https://www.rabe.de/en", "RABE")

    browser.close()
