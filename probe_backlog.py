from playwright.sync_api import sync_playwright
from scraper import scrape_landini

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    machines = scrape_landini(page, set())
    print(f"\n{len(machines)} machines au total")
    for m in machines:
        print(f"  {m.name} -> {m.specs[:200]}")
    browser.close()
