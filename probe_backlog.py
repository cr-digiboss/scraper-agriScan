from playwright.sync_api import sync_playwright
from scraper import scrape_mahindra

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    machines = scrape_mahindra(page, set())
    print(f"\n{len(machines)} machines au total")
    for m in machines[:5]:
        print(f"  {m.name} -> {m.specs[:200]}")
    browser.close()
