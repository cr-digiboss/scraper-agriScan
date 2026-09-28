"""
Script de sondage temporaire — à supprimer après usage.
Round 3 : McCormick n'a 0 table sur sa fiche produit. Dump du HTML brut
autour de mots-clés "specif"/"caractérist"/"technique" pour comprendre le
vrai format des données techniques (divs ? listes ? PDF uniquement ?).
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URL = "https://mccormick-tractors.com/fr/fr/produits/x8-vt-drive.html"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(15):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(300)

        text = page.inner_text("body")
        log.info(f"Longueur du texte visible : {len(text)}")
        log.info("----- 3000 premiers caractères -----")
        log.info(text[:3000])

        # cherche des sections potentielles de specs
        for kw in ["Caractéristique", "Spécification", "Technique", "Moteur", "Puissance", "kg", "cv", "PDF", "Télécharger"]:
            idx = text.find(kw)
            log.info(f"'{kw}' trouvé à l'index {idx}")

        # liens PDF éventuels
        pdf_links = page.eval_on_selector_all(
            "a[href$='.pdf'], a[href*='.pdf']", "els => els.map(e => e.href)"
        )
        log.info(f"\nLiens PDF : {pdf_links}")

        # tout élément avec class contenant 'spec' ou 'techn' ou 'carac'
        matching = page.eval_on_selector_all(
            "[class*='spec' i], [class*='techn' i], [class*='carac' i], [id*='spec' i]",
            "els => els.map(e => ({tag: e.tagName, cls: e.className, id: e.id, text: e.innerText.slice(0,200)}))"
        )
        log.info(f"\nÉléments avec classe spec/techn/carac : {len(matching)}")
        for m in matching[:10]:
            log.info(f"  {m}")

        browser.close()


if __name__ == "__main__":
    main()
