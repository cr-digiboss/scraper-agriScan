from playwright.sync_api import sync_playwright
import scraper

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_amazone(page, existing_keys=set())
    browser.close()

print(f"{len(machines)} machines")
for m in machines:
    print(f"- {m.name!r} categorie={m.category!r}")
