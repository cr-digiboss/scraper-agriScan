"""
Script de sondage temporaire — à supprimer après usage.
Validation de scrape_massey_ferguson() après correction de l'orientation
du tableau (les noms de modèle étaient inversés avec les libellés de specs).
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        machines = scraper.scrape_massey_ferguson(page, existing_keys=set())

        log.info(f"\nTOTAL : {len(machines)} machines")
        for m in machines[:15]:
            log.info(f"  name={m.name!r} category={m.category!r} specs={m.specs[:180]}")

        browser.close()


if __name__ == "__main__":
    main()
