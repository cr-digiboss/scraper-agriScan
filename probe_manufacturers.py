"""
Script de sondage temporaire — à supprimer après usage.
Dernier test : un délai de 20s entre la visite home et la fiche produit
suffit-il, si c'est bien une détection anti-bot basée sur la fréquence
des requêtes (pas le fait même d'une deuxième requête) ?
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
        page = context.new_page()
        page.goto(MCHALE_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        log.info("Attente de 20s avant la deuxième requête...")
        page.wait_for_timeout(20000)

        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        scroll_and_check(page, "E délai 20s entre home et produit")

        browser.close()


if __name__ == "__main__":
    main()
