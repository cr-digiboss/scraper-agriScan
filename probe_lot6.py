from playwright.sync_api import sync_playwright
import re

with sync_playwright() as p:
    browser = p.chromium.launch()

    # --- Pichon : refaire avec detection dynamique du domaine final ---
    print("=" * 70)
    print("PICHON")
    print("=" * 70)
    page = browser.new_page()
    page.goto("https://www.pichonindustries.com/en/", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    print("titre:", page.title())
    print("url finale:", page.url)
    final_root = page.url.split("//")[1].split("/")[0]
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "pichon" in h})
    print(f"{len(links)} liens 'pichon' trouves:")
    for l in links[:40]:
        print(" ", l)
    page.close()

    # --- Veenhuis : page categorie produits ---
    print("\n" + "=" * 70)
    print("VEENHUIS - categorie")
    print("=" * 70)
    page = browser.new_page()
    for url in [
        "https://veenhuis.com/en/products/application-of-manure/",
        "https://veenhuis.com/en/products/transporting-manure/",
    ]:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        print(f"\n-- {url} --  titre:", page.title())
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "veenhuis.com" in h})
        print(f"{len(links)} liens veenhuis:")
        for l in links[:30]:
            print(" ", l)
    page.close()

    # --- Bednar : page categorie produits ---
    print("\n" + "=" * 70)
    print("BEDNAR - categorie")
    print("=" * 70)
    page = browser.new_page()
    for url in [
        "https://www.bednar.com/en/combination-cultivators/",
        "https://www.bednar.com/en/compact-disc-harrows/",
    ]:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        print(f"\n-- {url} --  titre:", page.title())
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "bednar.com" in h})
        print(f"{len(links)} liens bednar:")
        for l in links[:30]:
            print(" ", l)
    page.close()

    browser.close()
