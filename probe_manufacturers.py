"""
Script de sondage temporaire — à supprimer après usage.
Validation finale de scrape_horsch() (parseur texte) avant merge.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))

        log.info("=== Horsch ===")
        horsch = scraper.scrape_horsch(page, existing_keys=set())
        log.info(f"TOTAL Horsch : {len(horsch)} machines")
        for m in horsch[:20]:
            log.info(f"  name={m.name!r} category={m.category!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        browser.close()


if __name__ == "__main__":
    main()
