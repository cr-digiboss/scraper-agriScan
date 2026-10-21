from playwright.sync_api import sync_playwright
import re

CATEGORIES = [
    "https://www.bednar.com/en/combination-cultivators/",
    "https://www.bednar.com/en/compact-disc-harrows/",
    "https://www.bednar.com/en/cutting-rollers/",
    "https://www.bednar.com/en/power-harrow/",
    "https://www.bednar.com/en/combination-subsoiler/",
    "https://www.bednar.com/en/fertiliser-and-seeds-hoppers/",
    "https://www.bednar.com/en/crop-residue-management/",
    "https://www.bednar.com/en/drill-masters/",
]

NAV_WORDS = {
    "24-hours-record", "a-test-ride", "agronomic-know-how", "blog", "calculator",
    "combination-cultivators", "combination-subsoiler", "compact-disc-harrows",
    "company", "contact", "crop-residue-management", "cutting-rollers",
    "dealer-area", "distribution-network", "download", "drill-masters",
    "easy-operation", "field-demo", "high-productivity", "history",
    "innovative-technology", "manufacturing", "news", "power-harrow",
    "press-kit", "fertiliser-and-seeds-hoppers",
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    all_products = set()
    for url in CATEGORIES:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "bednar.com/en/" in h})
        found = []
        for l in links:
            m = re.match(r"^https://www\.bednar\.com/en/([a-z0-9_-]+)/$", l)
            if m and m.group(1) not in NAV_WORDS:
                found.append(l)
        print(f"{url} -> {len(found)} liens produits candidats")
        for f in found:
            print("   ", f)
        all_products |= set(found)
    print(f"\nTOTAL: {len(all_products)} produits uniques sur toutes les categories testees")
    browser.close()
