"""
Script de validation temporaire — à supprimer après usage.
Appelle la VRAIE fonction de production scraper.scrape_new_holland(), en
limitant la découverte de liens à une seule page connue pour reproduire le
bug ("voir plus de modèles" / modèles absents du tableau de specs), pour
vérifier que le correctif capture bien les 9 modèles (6 du tableau + 3
cartes-only : 7630, 7635, 7641).
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("validate")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

TARGET = "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses/barres-de-coupe-varifeed-pour-moissonneuses-batteuses"

scraper.NEW_HOLLAND_CATEGORIES = [
    "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses",
]


def _patched_wait(page, base_path, **kwargs):
    return {TARGET}


scraper._wait_for_new_holland_links = _patched_wait


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        machines = scraper.scrape_new_holland(page, existing_keys=set())
        browser.close()

    names = sorted(m.name for m in machines)
    log.info(f"Total machines capturées : {len(machines)}")
    for n in names:
        log.info(f"  - {n}")

    expected_codes = ["7616", "7618", "7620", "7622", "7625", "7628", "7630", "7635", "7641"]
    log.info("\nVérification des 9 modèles attendus :")
    all_ok = True
    for code in expected_codes:
        found = any(code in n for n in names)
        log.info(f"  {code} : {'OK' if found else 'MANQUANT'}")
        if not found:
            all_ok = False

    log.info(f"\nRésultat global : {'SUCCES' if all_ok else 'ECHEC'}")

    for m in machines:
        if any(code in m.name for code in ("7630", "7635", "7641")):
            log.info(f"\nspecs de {m.name} :\n{m.specs}")


if __name__ == "__main__":
    main()
