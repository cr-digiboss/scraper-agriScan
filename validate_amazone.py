from playwright.sync_api import sync_playwright
import scraper

TEST_URLS = [
    "https://amazone.net/en/products-digital-solutions/agricultural-technology/fertilising-technology/mounted-spreader/za-m-mounted-spreader-51846",
    "https://amazone.net/en/products-digital-solutions/agricultural-technology/fertilising-technology/mounted-spreader/za-ts-mounted-spreader-51506",
    "https://amazone.net/en/products-digital-solutions/agricultural-technology/fertilising-technology/mounted-spreader/za-v-mounted-spreader-51654",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    for url in TEST_URLS:
        print("\n" + "=" * 70)
        print(url)
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        params = scraper._amazone_find_leaflet_params(page)
        print("params:", params)
        if not params:
            continue
        drucknummer, page_num = params
        import requests
        resp = requests.get(
            f"https://downloadcenter.amazone.de/file/view/printnumber/{drucknummer}/language/en-gb/doctype/leaflet",
            params={"page": page_num},
            headers={"User-Agent": "Mozilla/5.0", "Referer": url},
            timeout=30,
        )
        print("status:", resp.status_code, "bytes:", len(resp.content))
        base_name = scraper.clean(page.title()).split(" ")[0] if page.title() else ""
        print("base_name:", repr(base_name))
        specs = scraper._amazone_parse_spec_pdf(resp.content)
        for variant, s in specs.items():
            print(f"  variant={variant!r} -> {len(s)} attrs, ex: {list(s.items())[:4]}")

    browser.close()

print("\n" + "=" * 70)
print("Scrape complet (toutes categories)")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_amazone(page, existing_keys=set())
    browser.close()

print(f"\n{len(machines)} machines produites au total")
for m in machines[:30]:
    print(f"- {m.name!r} categorie={m.category!r} specs={m.specs[:200]}")
