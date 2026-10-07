"""
Script de validation temporaire — à supprimer avant la PR finale.
Appelle la vraie fonction de production scraper.scrape_kverneland(), mais en
limitant _kverneland_product_links à un petit échantillon fixe (les 2 pages
"une ligne par modèle" buggées + 2 pages classiques clé/valeur connues) pour
vérifier rapidement le correctif sans crawler tout le catalogue.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("validate")

SAMPLE_URLS = {
    "https://ien.kverneland.com/bale-choppers/mixer-feeders/selfline-4.0-compact",
    "https://ien.kverneland.com/bale-choppers/mixer-feeders/siloking-selfline-4.0-premium",
    "https://www.kverneland.com/farm-machinery/soil-tillage/mounted-ploughs/ES",
    "https://www.kverneland.com/farm-machinery/seeding/precision-drills/Optima-TFprofi",
}

scraper._kverneland_product_links = lambda page: SAMPLE_URLS


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))

        machines = scraper.scrape_kverneland(page, existing_keys=set())
        log.info(f"\n{len(machines)} machines au total")
        for m in machines:
            log.info(f"  - [{m.category}] {m.name!r} : {len(m.specs)} caractères de specs — {m.sourceUrl}")

        browser.close()


if __name__ == "__main__":
    main()
