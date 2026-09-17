"""
Script de sondage temporaire — à supprimer après usage.
Confirme que la fix consiste à utiliser une NOUVELLE page (pas celle qui
vient de charger la home) pour visiter chaque fiche produit.
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

        # Page 1 : sert uniquement à charger la home et lister les liens.
        home_page = context.new_page()
        home_page.goto(MCHALE_HOME, timeout=30000, wait_until="domcontentloaded")
        home_page.wait_for_timeout(4000)
        home_page.close()

        # Page 2 : nouvelle page dédiée, dont c'est la SEULE navigation.
        product_page = context.new_page()
        product_page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        product_page.wait_for_timeout(5000)
        scroll_and_check(product_page, "D nouvelle page dédiée par fiche produit")
        product_page.close()

        browser.close()


if __name__ == "__main__":
    main()
