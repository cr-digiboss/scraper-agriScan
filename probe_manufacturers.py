"""
Script de sondage temporaire — à supprimer après usage.
Lot 2 round 2 : URLs corrigées.
- Rauch : /fr/ 404 mais domaine répond -> dumper tous les liens de la page racine
- Sulky : sulky-burel.com/products/fertilisation/ trouvé via recherche web
- Berthoud : tester berthoud.fr/fr/ directement (évite la course de redirections)
- Bogballe : explorer la page /modeles/ (fonctionne déjà)
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


def dump(page, url, label, keyword_filter=None):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        log.info(f"\n=== {label} : {url} -> final={page.url} title={page.title()!r}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        netloc = urlparse(page.url).netloc
        same = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if netloc in urlparse(h).netloc))
        if keyword_filter:
            same = [h for h in same if keyword_filter(h)]
        log.info(f"  {len(same)} liens")
        for h in same[:60]:
            log.info(f"    {h}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        dump(page, "https://rauch.de/", "Rauch racine")
        dump(page, "https://www.sulky-burel.com/products/fertilisation/", "Sulky fertilisation")
        dump(page, "https://www.berthoud.fr/fr/", "Berthoud FR")
        dump(
            page, "https://www.bogballe.com/fr/epandeurs-dengrais/modeles/", "Bogballe modeles",
            keyword_filter=lambda h: "/modeles/" in h,
        )

        browser.close()


if __name__ == "__main__":
    main()
