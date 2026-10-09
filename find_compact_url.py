from playwright.sync_api import sync_playwright
import scraper

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(scraper.KVERNELAND_HOME, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    links = scraper._kverneland_product_links(page)
    compact_links = [l for l in links if "compact" in l.lower() or "mixer" in l.lower() or "feed" in l.lower()]
    print(f"{len(links)} liens au total, {len(compact_links)} liens 'compact/mixer/feed':")
    for l in compact_links:
        print(l)
    browser.close()
