"""
Script de sondage temporaire — à supprimer après usage.
Kubota, round 7 :
- Le bloc "Modèle | Puissance | Déclinaison | Transmission | Cylindrée"
  n'est PAS une <table> HTML mais un composant div stylé en tableau
  (a matché [class*='tab' i], donc une classe contenant "table").
  Il faut trouver la vraie structure DOM (classes, balises des lignes
  et cellules) pour pouvoir écrire un parseur.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect_kubota_dom(page, url):
    log.info(f"\n===== Kubota DOM : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(12):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)

        # trouver précisément l'élément conteneur du "tableau" de modèles
        candidates = page.query_selector_all("[class*='table' i]")
        log.info(f"  Éléments class*=table : {len(candidates)}")
        for el in candidates:
            txt = el.inner_text().strip().replace("\n", " ")
            if "Modèle" in txt and "Puissance" in txt:
                cls = el.get_attribute("class")
                tag = el.evaluate("e => e.tagName")
                log.info(f"  >>> Conteneur trouvé : <{tag} class='{cls}'>")
                # structure des enfants directs
                outer = el.evaluate("e => e.outerHTML")
                log.info(f"  Longueur outerHTML : {len(outer)}")
                log.info("  outerHTML (premiers 3000 car.) :")
                log.info("  " + outer[:3000])
                break
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


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

        inspect_kubota_dom(page, "https://ke.kubota-eu.com/agriculture/fr/products/m4003/")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
