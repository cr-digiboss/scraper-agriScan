"""
Script de sondage temporaire — à supprimer après usage.
Validation du correctif : les lignes où Déclinaison fusionne "Arceau" et
"Cabine" (specs concaténées sans séparateur) doivent être ignorées.
On ne revalide que la catégorie concernée (tracteurs spécialisés).
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

        # on ne garde que la catégorie problématique pour ce round
        scraper.KUBOTA_CATEGORIES = {
            "Tracteurs spécialisés": scraper.KUBOTA_CATEGORIES["Tracteurs spécialisés"],
        }

        machines = scraper.scrape_kubota(page, existing_keys=set())
        log.info(f"\nTOTAL : {len(machines)} machines (attendu : 2, sans merge Arceau/Cabine)")
        for m in machines:
            log.info(f"  - {m.name} | specs bruts : {m.specs}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
