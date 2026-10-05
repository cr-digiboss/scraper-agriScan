"""
Script de validation temporaire — à supprimer après usage.
Appelle la VRAIE fonction de production scraper.scrape_monosem() sur les
3 catégories réelles, pour vérifier qu'elle capture bien les variantes
(nom + specs) depuis les PDF "tableau général châssis", sans erreur.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("validate")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        machines = scraper.scrape_monosem(page, existing_keys=set())
        browser.close()

    log.info(f"\nTotal variantes capturées : {len(machines)}")
    for m in machines[:30]:
        log.info(f"  - [{m.category}] {m.name} ({m.variant})")
        log.info(f"      source: {m.sourceUrl}")
        log.info(f"      specs: {m.specs}")
    if len(machines) > 30:
        log.info(f"  ... (+{len(machines) - 30} autres)")


if __name__ == "__main__":
    main()
