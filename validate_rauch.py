from playwright.sync_api import sync_playwright
import scraper

TEST_URLS = [
    "https://rauch.de/en/fertiliser-spreaders/aero-gt/aero-gt-60-1.html",
    "https://rauch.de/en/fertiliser-spreaders/disc-spreader/axis-h/axis-h-30-2-emc-w.html",
    "https://rauch.de/en/fertiliser-spreaders/disc-spreader/mds/mds-14-2.html",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    for url in TEST_URLS:
        print("\n" + "=" * 70)
        print(url)
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        tables = page.query_selector_all("table")
        print(f"{len(tables)} tables")
        specs = scraper._rauch_parse_spec_tables(tables)
        for variant, s in specs.items():
            print(f"  variant={variant!r} -> {len(s)} attrs, ex: {list(s.items())[:3]}")

    browser.close()

print("\n" + "=" * 70)
print("Scrape complet (categories)")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_rauch(page, existing_keys=set())
    browser.close()

print(f"\n{len(machines)} machines produites au total")
for m in machines[:20]:
    print(f"- {m.name!r} categorie={m.category!r} specs={m.specs[:200]}")
