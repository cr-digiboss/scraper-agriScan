from playwright.sync_api import sync_playwright
import scraper

TEST_URLS = [
    # regression : transposed single-model table (bug) -> doit donner 1 machine
    "https://ien.kverneland.com/seeders/pneumatic-precision-drills/optima-r",
    "https://ien.kverneland.com/tillage-tools/rollers/kverneland-actiroll",
    "https://ien.kverneland.com/tillage-tools/subsoilers/kverneland-dtx",
    "https://ien.kverneland.com/seeders/pneumatic-mounted-seed-drills/e-drill-maxi-plus",
    # multi-modeles reel : doit toujours donner plusieurs machines distinctes
    "https://ien.kverneland.com/feeding/mixer-feeders/kverneland-compact",
]

scraper._kverneland_product_links = lambda page: set(TEST_URLS)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_kverneland(page, existing_keys=set())
    browser.close()

print(f"{len(machines)} machines produites au total")
for m in machines:
    print(f"- [{m.sourceUrl.split('/')[-1]}] {m.name!r} specs={m.specs[:150]}")
