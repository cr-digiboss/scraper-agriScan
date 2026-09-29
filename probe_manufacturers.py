"""
Script de sondage temporaire — à supprimer après usage.
Validation de scrape_bogballe(), scrape_sulky() et scrape_berthoud() (lot 2,
Rauch hors périmètre) avant merge.
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

        log.info("=== Bogballe ===")
        bogballe = scraper.scrape_bogballe(page, existing_keys=set())
        log.info(f"TOTAL Bogballe : {len(bogballe)} machines")
        for m in bogballe[:6]:
            log.info(f"  name={m.name!r} category={m.category!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        log.info("\n=== Sulky ===")
        sulky = scraper.scrape_sulky(page, existing_keys=set())
        log.info(f"TOTAL Sulky : {len(sulky)} machines")
        for m in sulky[:10]:
            log.info(f"  name={m.name!r} category={m.category!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        log.info("\n=== Berthoud ===")
        berthoud = scraper.scrape_berthoud(page, existing_keys=set())
        log.info(f"TOTAL Berthoud : {len(berthoud)} machines")
        for m in berthoud[:10]:
            log.info(f"  name={m.name!r} category={m.category!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        browser.close()


if __name__ == "__main__":
    main()
