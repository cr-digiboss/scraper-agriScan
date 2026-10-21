from playwright.sync_api import sync_playwright
import scraper

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ))
    machines = scraper.scrape_deutzfahr(page, existing_keys=set())
    browser.close()

print(f"\n{len(machines)} machines produites au total")
for m in machines[:40]:
    print(f"- {m.name!r} categorie={m.category!r} specs={m.specs[:250]}")
