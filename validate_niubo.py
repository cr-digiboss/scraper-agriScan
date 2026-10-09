from playwright.sync_api import sync_playwright
import scraper

TEST_CATEGORY_URL = "https://niubo.info/categoria_maquina/agricola/desbrozadoras-categoria/"
scraper.NIUBO_CATEGORIES = [TEST_CATEGORY_URL]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_niubo(page, existing_keys=set())
    browser.close()

print(f"{len(machines)} machines produites au total")
for m in machines:
    print(f"- [{m.sourceUrl.split('/')[-2]}] {m.name!r} categorie={m.category!r} specs={m.specs[:200]}")
