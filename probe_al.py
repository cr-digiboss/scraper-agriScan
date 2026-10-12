from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()

    # --- Amazone : explorer la home anglaise pour trouver le vrai chemin produits ---
    print("=" * 70)
    print("AMAZONE")
    print("=" * 70)
    page = browser.new_page()
    for url in [
        "https://www.amazone.net/",
        "https://amazone.de/en-gb",
        "https://amazone.de/en-en",
    ]:
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            print(f"\n-- {url} --")
            print("titre:", page.title())
            print("url finale:", page.url)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "amazone" in h})
            print(f"{len(links)} liens amazone trouves")
            for l in links[:30]:
                print(" ", l)
        except Exception as e:
            print(f"ERREUR {url}:", e)
    page.close()

    # --- Lely : explorer /global/ pour trouver le chemin produits ---
    print("\n" + "=" * 70)
    print("LELY")
    print("=" * 70)
    page = browser.new_page()
    for url in [
        "https://www.lely.com/global/",
        "https://www.lely.com/global/products/",
    ]:
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print(f"\n-- {url} --")
            print("titre:", page.title())
            print("url finale:", page.url)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "lely.com" in h})
            print(f"{len(links)} liens lely trouves")
            prod = [l for l in links if "product" in l.lower()]
            print(f"{len(prod)} liens contenant 'product':")
            for l in prod[:30]:
                print(" ", l)
        except Exception as e:
            print(f"ERREUR {url}:", e)
    page.close()

    browser.close()
