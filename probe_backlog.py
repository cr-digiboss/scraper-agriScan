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
        # Chercher tabs/accordions avec texte technique
        tech = page.query_selector_all("[class*='tech' i], [class*='spec' i], [class*='carac' i]")
        print(f"{len(tech)} elements tech/spec/carac-like")
        for el in tech[:5]:
            try:
                txt = el.inner_text().strip().replace("\n", " | ")
                if txt:
                    print("  tech:", txt[:300])
            except Exception:
                pass
        pdfs = page.eval_on_selector_all("a[href$='.pdf' i], a[href*='.pdf?' i]", "els => els.map(e => e.href)")
        print(f"{len(set(pdfs))} PDF:", sorted(set(pdfs))[:10])
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    inspect(page, "https://www.gregoire-besson.com/en/machines/cover", "GB cover")
    inspect(page, "https://www.gregoire-besson.com/en/machines/crossland", "GB crossland")

    inspect(page, "https://www.tecnoma.fr/", "TECNOMA home")
    inspect(page, "https://www.tecnoma.fr/produits/", "TECNOMA produits")

    browser.close()
