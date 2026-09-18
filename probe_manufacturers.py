"""
Script de sondage temporaire — à supprimer après usage.
Lot 6, round 5 : validation directe de scrape_kuhn() (le vrai code du
scraper, pas une réimplémentation) sur un sous-ensemble de catégories,
sans toucher Neon/Qdrant.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    # Sous-ensemble volontairement réduit pour un sondage rapide :
    # une catégorie simple (travail du sol) et une catégorie multi-sections
    # complexe (semoirs) pour vérifier les deux profils de page rencontrés.
    scraper.KUHN_CATEGORIES = {
        "Travail du sol": "https://www.kuhn.fr/grande-culture/materiels-de-travail-du-sol",
        "Semis": "https://www.kuhn.fr/grande-culture/semoirs",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="fr-FR",
        )
        page = context.new_page()

        machines = scraper.scrape_kuhn(page, existing_keys=set())

        log.info(f"\n===== RÉSULTAT : {len(machines)} machines extraites =====")
        for m in machines[:15]:
            log.info(f"  {m.brand} | {m.range} | {m.name} | cat={m.category}")
            log.info(f"    specs: {m.specs[:300]}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
