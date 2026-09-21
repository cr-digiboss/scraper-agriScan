"""
Script de sondage temporaire — à supprimer après usage.
Lot 7, round 6 : revalidation de scrape_valtra() après le fix de
désalignement d'en-tête (série F produisait des specs fausses avant le
fix ; on vérifie qu'elle est maintenant proprement ignorée, et que les
séries qui marchaient déjà (T, G, N, Q, S) donnent toujours les mêmes
bons résultats).
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
            viewport={"width": 1280, "height": 800},
            locale="fr-FR",
        )
        page = context.new_page()

        machines = scraper.scrape_valtra(page, existing_keys=set())
        log.info(f"\n===== Valtra : {len(machines)} machines extraites (round 6) =====")
        for m in machines:
            log.info(f"  {m.brand} | {m.range} | {m.name} | cat={m.category}")
            log.info(f"    specs: {m.specs}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
