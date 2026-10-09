from playwright.sync_api import sync_playwright
import scraper

TEST_URLS = [
    "https://agrisem.com/product/t-boss/",
    "https://agrisem.com/product/semoir-en-ligne-vibrosem/",
    "https://agrisem.com/product/boss-porte-monorampe/",  # PDF-only, doit etre ignore
]

scraper._agrisem_product_links = lambda page: set(TEST_URLS)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_agrisem(page, existing_keys=set())
    browser.close()

print(f"{len(machines)} machines produites au total")
for m in machines:
    print(f"- [{m.sourceUrl.split('/')[-2]}] {m.name!r} categorie={m.category!r} specs={m.specs[:150]}")
