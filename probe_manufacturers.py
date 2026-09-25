"""
Script de sondage temporaire — à supprimer après usage.
Kuhn : un utilisateur signale une fiche nommée "Coût de la main d'oeuvre
(€/h)" — un libellé de spec utilisé comme nom de machine, même famille de
bug que Massey Ferguson (PR #39). Round 1 : lancer scrape_kuhn() réel et
repérer les entrées suspectes + leur URL source pour inspection ciblée.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

MOTS_SUSPECTS = ["coût", "cout", "€/h", "main d'oeuvre", "main d’oeuvre"]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        machines = scraper.scrape_kuhn(page, existing_keys=set())

        log.info(f"\nTOTAL : {len(machines)} machines")
        suspects = [
            m for m in machines
            if any(mot in m.name.lower() for mot in MOTS_SUSPECTS)
        ]
        log.info(f"Entrées suspectes : {len(suspects)}")
        for m in suspects:
            log.info(f"  name={m.name!r} range={m.range!r} url={m.sourceUrl}")
            log.info(f"    specs={m.specs}")

        browser.close()


if __name__ == "__main__":
    main()
