from playwright.sync_api import sync_playwright
from scraper import scrape_weidemann, scrape_schaeffer

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

with sync_playwright() as p:
    browser = p.chromium.launch()

    page = browser.new_page(user_agent=UA)
    machines_w = scrape_weidemann(page, set())
    print(f"\n=== WEIDEMANN: {len(machines_w)} machines ===")
    for m in machines_w:
        print(f"  {m.name} ({m.category}) -> {m.specs[:200]}")

    page2 = browser.new_page(user_agent=UA)
    machines_s = scrape_schaeffer(page2, set())
    print(f"\n=== SCHAFFER: {len(machines_s)} machines ===")
    for m in machines_s:
        print(f"  {m.name} ({m.category}) -> {m.specs[:200]}")

    browser.close()
