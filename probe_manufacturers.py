"""
Script de sondage temporaire — à supprimer après usage.
Validation finale : appel direct de scraper.scrape_guttler() (le vrai
code de production) sur le catalogue complet Güttler.
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

        machines = scraper.scrape_guttler(page, existing_keys=set())
        log.info(f"\nTOTAL : {len(machines)} machines")
        for m in machines:
            log.info(f"  - {m.brand} | {m.range} | {m.name} | {m.category} | specs={len(m.specs)} car.")
            log.info(f"    specs bruts : {m.specs}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
