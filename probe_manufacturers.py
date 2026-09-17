"""
Script de sondage temporaire — à supprimer après usage.
Valide le fix corrigé de scrape_mchale (scroll jusqu'au bas réel de la
page au lieu d'une distance fixe insuffisante) en appelant directement
la vraie fonction du scraper contre le site réel, sans toucher à la
base de données (scrape_mchale ne fait qu'un GET + retourne des objets
Machine en mémoire).
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

        machines = scraper.scrape_mchale(page, existing_keys=set())

        log.info(f"\n{'=' * 80}\nRésultat : {len(machines)} machines extraites\n{'=' * 80}")
        for m in machines[:10]:
            log.info(f"  {m.brand} — {m.name} ({m.category}) : {len(m.specs)} caractères de specs JSON")
            log.info(f"    specs: {m.specs[:300]}")

        browser.close()


if __name__ == "__main__":
    main()
