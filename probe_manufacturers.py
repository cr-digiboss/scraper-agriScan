"""
Script de sondage temporaire — à supprimer après usage.
Lot 4 round 3 :
- Ropa : re-essai avec timeout plus long + dump liens de la page catégorie
- Holmer : accepte cookies DE puis dump liens de la page hub terra-dos
- Joskin : dump liens d'une page catégorie (épandeurs-de-lisier)
- Vredo : dump liens de la home FR + inspection solutions-agri pour voir
  s'il existe une vraie ligne de produits en FR
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
    "Cookies zulassen", "Auswahl erlauben", "Alle akzeptieren",
    "Nur notwendige Cookies verwenden",
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
        for i, t in enumerate(tables[:2]):
            rows = t.query_selector_all("tr")
            for r in rows[:6]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
        text = page.inner_text("body")
        log.info(f"    body text (700 car.) : {text[:700]!r}")
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
        dump_links(page, "https://www.ropa-maschinenbau.de/fr/produits/arracheuse-de-betteraves/", "Ropa catégorie arracheuse-de-betteraves")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.ropa-maschinenbau.de/fr/produits/arracheuse-de-betteraves/panther-2s/", "Ropa Panther 2S (retry)")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://www.holmer-maschinenbau.com/fr/produits/terra-dos", "Holmer terra-dos hub (retry cookies DE)")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://www.joskin.com/fr/%C3%A9pandeurs-de-lisier", "Joskin épandeurs-de-lisier")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://www.vredo.com/fr/", "Vredo home FR")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.vredo.com/fr/produits/solutions-agri/", "Vredo solutions-agri")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
