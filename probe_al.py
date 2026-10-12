import requests
from playwright.sync_api import sync_playwright

print("=" * 70)
print("SITEMAPS")
print("=" * 70)
for url in [
    "https://amazone.net/sitemap.xml",
    "https://amazone.net/en/sitemap.xml",
    "https://www.lely.com/sitemap.xml",
    "https://www.lely.com/global/sitemap.xml",
]:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        print(f"{url} -> {r.status_code}, {len(r.content)} bytes")
        if r.status_code == 200:
            print(r.text[:1000])
    except Exception as e:
        print(f"{url} -> ERREUR {e}")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    print("\n" + "=" * 70)
    print("AMAZONE - tous les liens /en/ contenant 'produc' ou nom de machine")
    print("=" * 70)
    page.goto("https://amazone.net/en", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    # Essaie de survoler/cliquer le menu "Products" si present
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    all_links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "amazone.net" in h})
    print(f"{len(all_links)} liens au total")
    for l in all_links:
        print(" ", l)

    print("\n" + "=" * 70)
    print("LELY - page /en/ (sans /global/)")
    print("=" * 70)
    for url in ["https://www.lely.com/en/", "https://www.lely.com/"]:
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print(f"\n-- {url} --  titre:", page.title(), " url finale:", page.url)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "lely.com" in h})
            print(f"{len(links)} liens:")
            for l in links:
                print(" ", l)
        except Exception as e:
            print(f"ERREUR {url}:", e)

    browser.close()
