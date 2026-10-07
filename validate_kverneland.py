"""
Script de validation temporaire — à supprimer avant la PR finale.
Appelle la vraie fonction scraper.scrape_kverneland() sur un échantillon
couvrant les deux régressions constatées :
- les 2 fiches "une ligne par modèle" (mixer-feeders) qui doivent toujours
  produire plusieurs machines ;
- les fiches à un seul modèle dont la table a une colonne vide en trop
  (Onyx, Helios, Arcadia) qui ne doivent PLUS produire une machine par
  ligne d'attribut, mais une seule machine avec toutes les specs.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("validate")

SAMPLE_URLS = {
    "https://ien.kverneland.com/bale-choppers/mixer-feeders/selfline-4.0-compact",
    "https://ien.kverneland.com/bale-choppers/mixer-feeders/siloking-selfline-4.0-premium",
    "https://ien.kverneland.com/weeders/inter-row-cultivators/kverneland-onyx-2000",
    "https://ien.kverneland.com/weeders/rotary-hoes/kverneland-helios-2000",
    "https://ien.kverneland.com/weeders/weeding-harrows/kverneland-arcadia-20000-f",
}

scraper._kverneland_product_links = lambda page: SAMPLE_URLS


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))

        machines = scraper.scrape_kverneland(page, existing_keys=set())
        log.info(f"\n{len(machines)} machines au total (attendu : 6 mixer-feeders + 1 par fiche a un seul modele = 9)")
        by_url = {}
        for m in machines:
            by_url.setdefault(m.sourceUrl, []).append(m.name)

        for url, names in by_url.items():
            log.info(f"\n{url} → {len(names)} machine(s) :")
            for n in names:
                log.info(f"  - {n!r}")

        browser.close()


if __name__ == "__main__":
    main()
