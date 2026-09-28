"""
Script de sondage temporaire — à supprimer après usage.
McCormick (mccormick-tractors.com) et Franquet (franquet.com) : nouvelles
marques à ajouter. Exploration de la structure de navigation et des fiches
produit avant d'écrire un scraper dédié.
"""

import logging

from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

MCCORMICK_HOME = "https://mccormick-tractors.com/fr/fr.html"
FRANQUET_HOME = "https://www.franquet.com/"


def inspect_home(page, url, label, netloc_filter):
    log.info(f"\n===== {label} : {url} =====")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"Statut HTTP : {resp.status if resp else 'N/A'}")
    except Exception as e:
        log.warning(f"Erreur navigation : {e}")
        return
    page.wait_for_timeout(4000)
    log.info(f"Titre : {page.title()}")
    log.info(f"URL finale : {page.url}")

    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    log.info(f"Nombre total de liens <a> : {len(hrefs)}")

    liens_pertinents = sorted(set(
        h for h in hrefs
        if netloc_filter in urlparse(h).netloc
    ))
    log.info(f"Liens vers {netloc_filter} : {len(liens_pertinents)}")
    for h in liens_pertinents[:60]:
        log.info(f"  {h}")

    tables = page.query_selector_all("table")
    log.info(f"Nombre de tables sur la page d'accueil : {len(tables)}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        inspect_home(page, MCCORMICK_HOME, "McCormick", "mccormick-tractors.com")
        inspect_home(page, FRANQUET_HOME, "Franquet", "franquet.com")

        browser.close()


if __name__ == "__main__":
    main()
