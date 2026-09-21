"""
Script de sondage temporaire — à supprimer après usage.
Lot 7, round 5 : validation directe de scrape_jcb() et scrape_valtra()
(le vrai code du scraper), sur un sous-ensemble réduit, sans toucher
Neon/Qdrant.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    # JCB : 2 catégories (une "agricole", une "construction") pour vérifier
    # que le parser générique fonctionne sur les deux profils de page.
    scraper.JCB_CATEGORIES = {
        "Tracteurs": "https://www.jcb.com/fr-FR/products/machines/tracteurs/",
        "Télescopiques rotatifs": "https://www.jcb.com/fr-FR/products/machines/rotating-telehandlers/",
    }
    # Valtra : toutes les séries (léger, 7 pages sans crawl produit).

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

        jcb_machines = scraper.scrape_jcb(page, existing_keys=set())
        log.info(f"\n===== JCB : {len(jcb_machines)} machines extraites =====")
        for m in jcb_machines[:10]:
            log.info(f"  {m.brand} | {m.range} | {m.name} | cat={m.category}")
            log.info(f"    specs: {m.specs[:250]}")

        valtra_machines = scraper.scrape_valtra(page, existing_keys=set())
        log.info(f"\n===== Valtra : {len(valtra_machines)} machines extraites =====")
        for m in valtra_machines[:15]:
            log.info(f"  {m.brand} | {m.range} | {m.name} | cat={m.category}")
            log.info(f"    specs: {m.specs[:250]}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
