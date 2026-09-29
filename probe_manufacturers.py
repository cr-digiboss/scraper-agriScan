"""
Script de sondage temporaire — à supprimer après usage.
Lot 2 round 4 :
- Bogballe : inspecter une fiche modèle (m60w-plus)
- Sky Agriculture (ex-Sulky) : catégorie epandeurs-portes -> fiches produit
- Berthoud : chercher la gamme "Grandes Cultures" (agricole pro, pas jardin)
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


def accept_cookies(page):
    for text in ["Tout accepter", "Accepter tout", "Accept all", "J'accepte", "Accepter"]:
        try:
            btn = page.get_by_text(text, exact=False).first
            if btn.is_visible(timeout=1500):
                btn.click(timeout=1500)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


def inspect_product(page, url, label):
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
            log.info(f"    table {i}: {len(rows)} lignes")
            for r in rows[:6]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
        spec_divs = page.query_selector_all("[class*='spec' i], [class*='caract' i], [class*='fact' i]")
        log.info(f"    {len(spec_divs)} div(s) spec/caract/fact")
        text = page.inner_text("body")
        log.info(f"    body text (900 car.) : {text[:900]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def dump_links(page, url, label, keyword_filter=None):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1000)
        log.info(f"\n=== {label} : {url} title={page.title()!r}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        netloc = urlparse(page.url).netloc
        same = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if netloc in urlparse(h).netloc))
        if keyword_filter:
            same = [h for h in same if keyword_filter(h)]
        log.info(f"  {len(same)} liens")
        for h in same[:40]:
            log.info(f"    {h}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        inspect_product(page, "https://www.bogballe.com/fr/epandeurs-dengrais/modeles/m60w-plus/", "Bogballe M60W-Plus")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://sky-agriculture.com/produits/epandeurs-portes/", "Sky Agriculture epandeurs-portes")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(
            page, "https://www.berthoud.fr/fr/", "Berthoud FR recherche grandes cultures",
            keyword_filter=lambda h: "grande" in h.lower() or "agricol" in h.lower() or "professionnel" in h.lower(),
        )
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://www.berthoud.com/gamme-grandes-cultures/", "Berthoud.com gamme grandes cultures")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
