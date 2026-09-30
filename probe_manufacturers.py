"""
Script de sondage temporaire — à supprimer après usage.
Lot 5 round 2 :
- Samson : fiche produit (epandeurs/samson-flex-ii) pour voir la structure des specs
- Pichon : fiche gamme (gamme-pichon/gamme-mk) pour voir la structure des specs
- Veenhuis : dump de home.veenhuis.com pour trouver le vrai catalogue
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

COOKIE_TEXTS = [
    "Tout accepter", "Accepter tout", "Accept all", "J'accepte", "Accepter",
]


def accept_cookies(page):
    for text in COOKIE_TEXTS:
        try:
            btn = page.get_by_text(text, exact=False).first
            if btn.is_visible(timeout=1500):
                btn.click(timeout=1500)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


def inspect(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1500)
        log.info(f"\n--- {label} : {url} title={page.title()!r}")
        tables = page.query_selector_all("table")
        log.info(f"    {len(tables)} table(s)")
        for i, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"    table {i}: {len(rows)} rows")
            for r in rows[:8]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
        text = page.inner_text("body")
        log.info(f"    body text (900 car.) : {text[:900]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def dump_links(page, url, label):
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        accept_cookies(page)
        page.wait_for_timeout(1000)
        log.info(f"\n=== {label} : {url} title={page.title()!r}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        netloc = urlparse(page.url).netloc
        same = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if netloc in urlparse(h).netloc))
        log.info(f"  {len(same)} liens")
        for h in same[:80]:
            log.info(f"    {h}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.samson-agro.com/fr/epandeurs/samson-flex-ii/", "Samson Flex II")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.pichonindustries.fr/gamme-pichon/gamme-mk/", "Pichon gamme MK")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://home.veenhuis.com/fr", "Veenhuis home.veenhuis.com FR")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
