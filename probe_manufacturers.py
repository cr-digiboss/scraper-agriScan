"""
Script de sondage temporaire — à supprimer après usage.
John Deere, round 8 : validation directe de scrape_johndeere() (le vrai
code du scraper) sur une seule catégorie (Tracteurs), sans toucher
Neon/Qdrant.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    scraper.JOHNDEERE_CATEGORIES = {
        "Tracteurs": "https://www.deere.fr/fr-fr/produits-et-solutions/tracteurs",
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

        machines = scraper.scrape_johndeere(page, existing_keys=set())

        log.info(f"\n===== RÉSULTAT : {len(machines)} machines extraites =====")
        for m in machines[:20]:
            log.info(f"  {m.brand} | {m.range} | {m.name} | cat={m.category}")
            log.info(f"    specs: {m.specs[:350]}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
