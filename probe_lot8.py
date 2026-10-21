from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()

    # --- Landini : plus de temps + variante URL ---
    print("=" * 70)
    print("LANDINI")
    print("=" * 70)
    page = browser.new_page()
    for url in ["https://www.landini.it/en/", "https://www.landini.it/en/tractors"]:
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(2000)
            print(f"\n-- {url} --  titre:", page.title(), " url finale:", page.url)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "landini" in h})
            print(f"{len(links)} liens:")
            for l in links[:25]:
                print(" ", l)
        except Exception as e:
            print(f"-- {url} -- ERREUR:", e)
    page.close()

    # --- Merlo : bonne URL ---
    print("\n" + "=" * 70)
    print("MERLO")
    print("=" * 70)
    page = browser.new_page()
    for url in ["https://www.merlo.com/en/int/products", "https://www.merlo.com/en/int/"]:
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print(f"\n-- {url} --  titre:", page.title(), " url finale:", page.url)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "merlo.com" in h})
            print(f"{len(links)} liens:")
            for l in links[:30]:
                print(" ", l)
        except Exception as e:
            print(f"-- {url} -- ERREUR:", e)
    page.close()

    # --- Pellenc : page categorie produit ---
    print("\n" + "=" * 70)
    print("PELLENC - categorie")
    print("=" * 70)
    page = browser.new_page()
    for url in [
        "https://www.pellenc.com/en-gb/our-products/fruit-growing-and-olive-growing/fruit-growing/cutting",
        "https://www.pellenc.com/en-gb/our-products/from-the-vineyard-to-the-winery/vine-growing/battery-powered-tools",
    ]:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        print(f"\n-- {url} --  titre:", page.title())
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "pellenc.com" in h})
        print(f"{len(links)} liens:")
        for l in links[:30]:
            print(" ", l)
    page.close()

    browser.close()
