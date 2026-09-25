"""
Script de sondage temporaire — à supprimer après usage.
Validation de scrape_marque() après retrait de l'année du champ variant.
Utilise Deutz-Fahr (43 modèles, petite marque) pour un run rapide.
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

        machines = scraper.scrape_marque(
            page, "Deutz-Fahr", scraper.MARQUES["Deutz-Fahr"], existing_keys=set()
        )

        log.info(f"\nTOTAL : {len(machines)} machines")
        variants_non_vides = [m for m in machines if m.variant]
        log.info(f"Machines avec variant non vide : {len(variants_non_vides)} (attendu : 0)")

        noms = {}
        for m in machines:
            noms.setdefault(m.name, 0)
            noms[m.name] += 1
        doublons = {n: c for n, c in noms.items() if c > 1}
        log.info(f"Noms en double dans le même run (auraient été distincts par année avant) : {len(doublons)}")
        for n, c in list(doublons.items())[:10]:
            log.info(f"  {n} → {c} occurrences")

        for m in machines[:5]:
            log.info(f"  ex: {m.name} | variant={m.variant!r} | annee_specs={m.specs}")

        browser.close()


if __name__ == "__main__":
    main()
