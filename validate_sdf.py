"""
Script de validation temporaire — à supprimer avant la PR finale.
Appelle les vraies fonctions de production scraper.scrape_deutz_fahr() et
scraper.scrape_same() directement, avec existing_keys=set() pour voir tout
ce qu'elles trouvent.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("validate")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))

        for brand, fn in [("Deutz-Fahr", scraper.scrape_deutz_fahr), ("Same", scraper.scrape_same)]:
            log.info(f"\n{'='*70}\n{brand}")
            machines = fn(page, existing_keys=set())
            log.info(f"\n{brand} : {len(machines)} machines au total")
            for m in machines:
                log.info(f"  - {m.name} / {m.variant} : {len(m.specs)} caractères de specs")

        browser.close()


if __name__ == "__main__":
    main()
