"""
Script de sondage temporaire — à supprimer après usage.
Validation des nouveaux scrapers McCormick et Franquet avant merge :
lance scrape_mccormick() et scrape_franquet() réels (pas de réimplémentation)
et affiche les machines trouvées pour vérification manuelle.
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

        log.info("=== McCormick ===")
        mccormick = scraper.scrape_mccormick(page, existing_keys=set())
        log.info(f"TOTAL McCormick : {len(mccormick)} machines")
        for m in mccormick[:10]:
            log.info(f"  name={m.name!r} range={m.range!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        log.info("\n=== Franquet ===")
        franquet = scraper.scrape_franquet(page, existing_keys=set())
        log.info(f"TOTAL Franquet : {len(franquet)} machines")
        for m in franquet[:15]:
            log.info(f"  name={m.name!r} range={m.range!r} variant={m.variant!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        browser.close()


if __name__ == "__main__":
    main()
