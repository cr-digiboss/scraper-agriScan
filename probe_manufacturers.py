"""
Script de sondage temporaire — à supprimer après usage.
Güttler, round 7 : vérifier une éventuelle pagination sur la page
produits française (12 fiches trouvées semble faible vu les 8+
catégories du site allemand — Frontpacker, Packerwalzen, etc.).
"""

import logging
import re

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


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

        url = "https://guttler.org/fr/produits/"
        log.info(f"\n===== {url} =====")
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(15):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(300)

        body_text = page.inner_text("body")
        log.info(f"  Longueur texte body : {len(body_text)}")
        # chercher des indices de pagination
        for kw in ["page 2", "Page 2", "Suivant", "suivant", "»", "Charger plus", "charger plus"]:
            if kw in body_text:
                idx = body_text.find(kw)
                log.info(f"  Trouvé '{kw}' à l'index {idx} : ...{body_text[max(0,idx-80):idx+80]}...")

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        page_links = sorted(set(h for h in hrefs if re.search(r"/page/\d+", h) or "paged=" in h))
        log.info(f"  Liens de pagination détectés : {len(page_links)}")
        for p_ in page_links:
            log.info(f"    {p_}")

        product_links = sorted(set(
            h.split("?")[0].split("#")[0] for h in hrefs
            if "guttler.org/fr/produit/" in h
        ))
        log.info(f"  Total liens produits sur cette page : {len(product_links)}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
