"""
Script de sondage temporaire — à supprimer après usage.
John Deere, round 7 : cartographier les sous-catégories et liens produits
(pattern /produits-solutions/...) des autres familles (récolte, tondeuses,
Gator, foin/fourrage) avant d'écrire le scraper.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

CATEGORIES = {
    "Récolte": "https://www.deere.fr/fr-fr/produits-et-solutions/recolte",
    "Tondeuses": "https://www.deere.fr/fr-fr/produits-et-solutions/tondeuses",
    "Gator": "https://www.deere.fr/fr-fr/produits-et-solutions/vehicules-utilitaires-gator",
    "Foin et fourrage": "https://www.deere.fr/fr-fr/produits-et-solutions/equipement-pour-le-foin-et-le-fourrage",
}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            viewport={"width": 1280, "height": 1600},
        )
        page = context.new_page()

        for name, url in CATEGORIES.items():
            log.info(f"\n===== {name} : {url} =====")
            try:
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(3500)
                for _ in range(8):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(300)
                title = page.title()
                log.info(f"  Titre : {title}")
                hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                seen = set()
                produits = []
                sous_cat = []
                for href in hrefs:
                    u = urlparse(href)
                    if "deere.fr" not in u.netloc:
                        continue
                    clean_h = href.split("?")[0].split("#")[0]
                    if clean_h in seen:
                        continue
                    seen.add(clean_h)
                    if "/produits-solutions/" in clean_h:
                        produits.append(clean_h)
                    elif "/produits-et-solutions/" in clean_h and clean_h.rstrip("/") != url.rstrip("/"):
                        sous_cat.append(clean_h)
                log.info(f"  Liens produits (produits-solutions) : {len(produits)}")
                for pr in produits[:15]:
                    log.info(f"    {pr}")
                log.info(f"  Liens sous-catégories (produits-et-solutions) : {len(sous_cat)}")
                for sc in sous_cat[:15]:
                    log.info(f"    {sc}")
            except Exception as e:
                log.info(f"  ERREUR : {e!r}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
