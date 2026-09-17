"""
Script de sondage temporaire — à supprimer après usage.
scrape_mchale échoue toujours (0 specs) même avec la recette exacte
(vrais wheel events, 10x2000px/500ms, 5s d'attente) qui avait marché en
sondage isolé. Seule différence restante : scrape_mchale navigue vers
la page d'accueil McHale AVANT la fiche produit (pour lister les liens),
alors que le sondage réussi allait directement sur l'URL produit.
Compare les deux scénarios sur la même URL, dans le même run.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

MCHALE_HOME = "https://www.mchale.net/"
URL = "https://www.mchale.net/products/691-round-bale-handler/"


def scroll_and_check(page, label):
    for _ in range(10):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(500)
    spec_els = page.query_selector_all("[class*='spec' i], [class*='technical' i]")
    log.info(f"[{label}] Éléments [class*=spec/technical] : {len(spec_els)}")
    return len(spec_els)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            viewport={"width": 1280, "height": 800},
        )

        # Scénario A : navigation directe (comme le sondage qui avait marché)
        page_a = context.new_page()
        page_a.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page_a.wait_for_timeout(5000)
        scroll_and_check(page_a, "A directe")
        page_a.close()

        # Scénario B : home d'abord, puis la fiche produit (comme scrape_mchale)
        page_b = context.new_page()
        page_b.goto(MCHALE_HOME, timeout=30000, wait_until="domcontentloaded")
        page_b.wait_for_timeout(4000)
        page_b.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page_b.wait_for_timeout(5000)
        scroll_and_check(page_b, "B home-puis-produit")
        page_b.close()

        # Scénario C : comme B mais sur un NOUVEAU contexte (cookies/session isolés)
        context2 = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            viewport={"width": 1280, "height": 800},
        )
        page_c = context2.new_page()
        page_c.goto(MCHALE_HOME, timeout=30000, wait_until="domcontentloaded")
        page_c.wait_for_timeout(4000)
        page_c.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page_c.wait_for_timeout(5000)
        scroll_and_check(page_c, "C nouveau contexte, home-puis-produit")
        page_c.close()

        browser.close()


if __name__ == "__main__":
    main()
