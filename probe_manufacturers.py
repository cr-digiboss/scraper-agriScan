"""
Script de validation temporaire — à supprimer après usage.
Appelle directement scrape_franquet() (fonction réelle de production) pour
valider le nouveau parseur avant merge.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("validate")


def main():
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

        machines = scraper.scrape_franquet(page, existing_keys=set())
        log.info(f"\n=== RÉSULTAT : {len(machines)} machines Franquet ===")
        for m in machines:
            log.info(f"  - {m.name} | variant={m.variant!r} ({m.category}) : {len(m.specs)} car. de specs")
        if machines:
            log.info(f"\nExemple specs ({machines[0].name} / {machines[0].variant}):\n{machines[0].specs}")
            # affiche aussi un exemple avec plusieurs valeurs pour vérifier l'alignement colspan
            for m in machines:
                if "Largeur" in m.specs or "largeur" in m.specs.lower():
                    log.info(f"\nExemple avec attribut largeur ({m.name} / {m.variant}):\n{m.specs}")
                    break

        browser.close()


if __name__ == "__main__":
    main()
