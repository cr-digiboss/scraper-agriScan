"""
Script de sondage temporaire — à supprimer après usage.
Validation du correctif : la table parasite (sélecteur pays/langue) sur
la fiche Swativo (andaineurs à bande) ne doit plus produire de fausses
machines. On ne revalide que cette page pour aller vite.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # ne garder que la page connue pour avoir la table parasite
        scraper._krone_product_links = lambda page: {
            "https://www.krone.fr/produits/andaineurs-a-bande/swativo"
        }

        machines = scraper.scrape_krone(page, existing_keys=set())
        log.info(f"\nTOTAL : {len(machines)} machines (attendu : 0, aucune table réelle sur cette fiche)")
        for m in machines:
            log.info(f"  - {m.name} | specs bruts : {m.specs}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
