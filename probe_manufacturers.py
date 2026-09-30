"""
Script de sondage temporaire — à supprimer après usage.
Lot 4 round 4 :
- Ropa : clique "CARACTÉRISTIQUES TECHNIQUES" sur panther-2s puis inspecte le tableau ;
  dump des liens de /fr/produits/ (page parente) pour lister toutes les familles
- Joskin : inspecte une fiche modèle réelle (epandeurs-de-lisier/alpina2)
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


def dump_tables(page, label):
    tables = page.query_selector_all("table")
    log.info(f"    {len(tables)} table(s)")
    for i, t in enumerate(tables[:3]):
        rows = t.query_selector_all("tr")
        log.info(f"    table {i}: {len(rows)} rows")
        for r in rows[:8]:
            cells = r.query_selector_all("td, th")
            log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")


def ropa_click_specs(page, url):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1000)
        log.info(f"\n--- Ropa Panther 2S : title avant clic = {page.title()!r}")
        try:
            tab = page.get_by_text("CARACTÉRISTIQUES TECHNIQUES", exact=False).first
            tab.click(timeout=5000)
            page.wait_for_timeout(2000)
        except Exception as e:
            log.warning(f"    clic échec : {e}")
        log.info(f"    title après clic = {page.title()!r}")
        dump_tables(page, "ropa")
        if not page.query_selector_all("table"):
            text = page.inner_text("body")
            log.info(f"    body text post-clic (1200 car.) : {text[:1200]!r}")
    except Exception as e:
        log.warning(f"  Ropa : échec ({e})")


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


def inspect(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1500)
        log.info(f"\n--- {label} : {url} title={page.title()!r}")
        dump_tables(page, label)
        text = page.inner_text("body")
        log.info(f"    body text (700 car.) : {text[:700]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        ropa_click_specs(page, "https://www.ropa-maschinenbau.de/fr/produits/arracheuse-de-betteraves/panther-2s/")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://www.ropa-maschinenbau.de/fr/produits/", "Ropa produits (page parente, toutes familles)")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.joskin.com/fr/epandeurs-de-lisier/alpina2", "Joskin Alpina2")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
