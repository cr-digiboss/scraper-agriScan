from playwright.sync_api import sync_playwright
import scraper

TEST_URLS = [
    "https://www.einboeck.at/produkte/bodenbearbeitung/feingrubber/vibrostar/",
    "https://www.einboeck.at/produkte/bodenbearbeitung/flachgrubber/razor/",
    "https://www.einboeck.at/produkte/ackerkulturpflege/striegeltechnik/hackstriegel-aerostar-classic/",
    "https://www.einboeck.at/produkte/ackerkulturpflege/dammpflegetechnik/chopstar-hill/",
]

scraper._einboeck_product_links = lambda page: set(TEST_URLS)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_einboeck(page, existing_keys=set())
    browser.close()

print(f"{len(machines)} machines produites au total")
for m in machines:
    print(f"- [{m.sourceUrl.split('/')[-2]}] {m.name!r} categorie={m.category!r} specs={m.specs[:200]}")
