"""
Script de validation temporaire — à supprimer avant la PR finale.
Appelle la vraie fonction de production scraper.scrape_pottinger() en limitant
POTTINGER_CATEGORIES à "Faucheuses" (contient la page Alpha Motion, qui a 2
tables / 5 modèles au total) pour vérifier rapidement que le correctif
(parcourir toutes les <table> au lieu de seulement tables[0]) fonctionne.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("validate")

scraper.POTTINGER_CATEGORIES = {
    "Faucheuses": "https://www.poettinger.at/fr_be/produkte/kategorie/mw/faucheuses",
}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))

        machines = scraper.scrape_pottinger(page, existing_keys=set())
        log.info(f"\n{len(machines)} machines au total (Faucheuses uniquement)")

        alpha_motion = [m for m in machines if "ALPHA MOTION" in m.name.upper()]
        log.info(f"\n{len(alpha_motion)} modèles 'Alpha Motion' trouvés :")
        for m in alpha_motion:
            log.info(f"  - {m.name}")

        browser.close()


if __name__ == "__main__":
    main()
