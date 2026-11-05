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
        for ti, t in enumerate(tables):
            txt = t.inner_text().strip().replace("\n", " | ")
            print(f"  table {ti}:", txt[:400])
        tech = page.query_selector_all(
            "[class*='tech' i], [class*='spec' i], [class*='data' i], [class*='carac' i], dl"
        )
        print(f"\n{len(tech)} elements tech/spec/data-like")
        for el in tech[:8]:
            try:
                txt = el.inner_text().strip().replace("\n", " | ")
                if txt and len(txt) > 20:
                    print("  tech:", txt[:400])
            except Exception:
                pass
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    inspect(page, "https://www.weidemann.de/produkte/hoflader/hoftrac-1160", "WEIDEMANN hoftrac-1160")
    inspect(page, "https://www.schaeffer.de/en/products/10/compact-loader-4670", "SCHAFFER compact-loader-4670")

    browser.close()
