"""
Script de sondage temporaire — à supprimer après usage.
Lot 5, round 4 : dump du contenu des éléments [class*=spec] sur la fiche
Horsch Joker RT (0 table trouvée, mais 6 éléments matchent ce sélecteur).
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URL = "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques/joker-rt"


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
        page.goto(URL, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(400)

        els = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='daten' i]")
        log.info(f"Éléments trouvés : {len(els)}")
        for i, el in enumerate(els):
            cls = el.get_attribute("class") or ""
            tag = el.evaluate("e => e.tagName")
            txt = el.inner_text()
            log.info(f"\n--- Élément {i} <{tag} class=\"{cls}\"> ({len(txt)} car.) ---")
            log.info(txt[:600])

        browser.close()


if __name__ == "__main__":
    main()
