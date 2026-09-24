"""
Script de sondage temporaire — à supprimer après usage.
Validation de scrape_guttler() après le fix de complétude (sitemap + hreflang).
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

        machines = scraper.scrape_guttler(page, existing_keys=set())

        log.info(f"\nTOTAL : {len(machines)} machines")
        ranges = {}
        for m in machines:
            ranges.setdefault(m.range, 0)
            ranges[m.range] += 1
        log.info(f"Nombre de fiches produit distinctes (range) : {len(ranges)}")
        for r, n in sorted(ranges.items()):
            log.info(f"  {r} → {n} modèles")

        browser.close()


if __name__ == "__main__":
    main()
