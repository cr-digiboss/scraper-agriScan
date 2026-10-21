from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()

    # --- Vredo : page categorie ---
    print("=" * 70)
    print("VREDO - categories")
    print("=" * 70)
    page = browser.new_page()
    for url in [
        "https://www.vredo.com/en/products/agri-solutions/agricultural-overseeders/",
        "https://www.vredo.com/en/products/agri-solutions/slurry-injection/",
    ]:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        print(f"\n-- {url} --  titre:", page.title())
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "vredo.com" in h})
        print(f"{len(links)} liens vredo:")
        for l in links[:30]:
            print(" ", l)
    page.close()

    # --- Manitou : essayer d'autres URLs d'entree ---
    print("\n" + "=" * 70)
    print("MANITOU - tentatives")
    print("=" * 70)
    page = browser.new_page()
    for url in [
        "https://www.manitou.com/en/products",
        "https://www.manitou.com/",
        "https://www.manitou-group.com/en/",
    ]:
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            print(f"\n-- {url} --  titre:", page.title(), " url finale:", page.url)
        except Exception as e:
            print(f"-- {url} -- ERREUR:", e)
    page.close()

    # --- Maschio Gaspardo : essayer d'autres URLs ---
    print("\n" + "=" * 70)
    print("MASCHIO GASPARDO - tentatives")
    print("=" * 70)
    page = browser.new_page()
    for url in [
        "https://www.maschio.com/en/",
        "https://www.gaspardo.it/en/",
        "https://www.maschionet.com/",
    ]:
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            print(f"\n-- {url} --  titre:", page.title(), " url finale:", page.url)
        except Exception as e:
            print(f"-- {url} -- ERREUR:", e)
    page.close()

    browser.close()
