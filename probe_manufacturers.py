"""
Script de sondage temporaire — à supprimer après usage.
Validation de scrape_horsch() et scrape_vicon() (appel des vraies fonctions)
avant merge, lot 1 partiel (Amazone et Maschio Gaspardo reportés).
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

        log.info("=== Vicon ===")
        vicon = scraper.scrape_vicon(page, existing_keys=set())
        log.info(f"TOTAL Vicon : {len(vicon)} machines")
        for m in vicon[:10]:
            log.info(f"  name={m.name!r} category={m.category!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        log.info("\n=== Horsch ===")
        horsch = scraper.scrape_horsch(page, existing_keys=set())
        log.info(f"TOTAL Horsch : {len(horsch)} machines")
        for m in horsch[:15]:
            log.info(f"  name={m.name!r} category={m.category!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        browser.close()


if __name__ == "__main__":
    main()
