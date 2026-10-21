from playwright.sync_api import sync_playwright
import scraper

TEST_URLS = [
    "https://www.bednar.com/en/atlas-ae_profi/",
    "https://www.bednar.com/en/swifterdisc-xe/",
    "https://www.bednar.com/en/terraland_do/",
    "https://www.bednar.com/en/mulcher-mm/",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    for url in TEST_URLS:
        print("\n" + "=" * 70)
        print(url)
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        tables = page.query_selector_all("table")
        rows_by_table = [t.query_selector_all("tr") for t in tables]
        parsed_tables = [
            [[scraper.clean(c.inner_text()) for c in r.query_selector_all("td, th")] for r in rows]
            for rows in rows_by_table
        ]
        base_name, specs = scraper._bednar_parse_spec_table(parsed_tables)
        print("base_name:", repr(base_name))
        for variant, s in specs.items():
            print(f"  variant={variant!r} -> {len(s)} attrs, ex: {list(s.items())[:4]}")

    browser.close()

print("\n" + "=" * 70)
print("Scrape complet (toutes categories)")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_bednar(page, existing_keys=set())
    browser.close()

print(f"\n{len(machines)} machines produites au total")
for m in machines[:40]:
    print(f"- {m.name!r} categorie={m.category!r} specs={m.specs[:200]}")
