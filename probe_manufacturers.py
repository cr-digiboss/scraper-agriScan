"""
Script de sondage temporaire — à supprimer après usage.
Lot 2 round 3 :
- Rauch : contenu servi en allemand malgré tout, chercher la version FR
  (land-waehlen.html = sélecteur de pays, ou header Accept-Language)
- Sulky : ERR_CONNECTION_REFUSED sur 2 chemins différents -> probablement
  bloqué depuis cet environnement, retester avec une page fraîche pour
  écarter un bug de script
- Berthoud / Bogballe : ré-tester avec une page fraîche (le round 2 a eu des
  navigations interrompues à cause de la réutilisation de la même page)
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

        # Rauch : chercher la version FR
        page = browser.new_page(user_agent=UA, locale="fr-FR", extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9"})
        dump(page, "https://rauch.de/land-waehlen.html", "Rauch land-waehlen")
        page.close()

        page = browser.new_page(user_agent=UA, locale="fr-FR", extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9"})
        dump(page, "https://rauch.de/", "Rauch racine (Accept-Language fr)")
        page.close()

        # Sulky : retest isolé
        page = browser.new_page(user_agent=UA)
        dump(page, "https://www.sulky-burel.com/", "Sulky racine (page fraîche)")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump(page, "https://sky-agriculture.com/fr/", "Sky Agriculture FR (page fraîche)")
        page.close()

        # Berthoud / Bogballe : retest isolé
        page = browser.new_page(user_agent=UA)
        dump(page, "https://www.berthoud.fr/fr/", "Berthoud FR (page fraîche)")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump(
            page, "https://www.bogballe.com/fr/epandeurs-dengrais/modeles/", "Bogballe modeles (page fraîche)",
            keyword_filter=lambda h: "/modeles/" in h,
        )
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
