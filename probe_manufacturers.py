"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland round 6 : confirmé (round 5) que les codes 7630/7635/
7641 sont absents du <table> (texte ET HTML). On inspecte le texte
INTEGRAL (non tronqué) d'une carte de la galerie "MODÈLES" pour savoir
si elle contient d'autres données structurées exploitables (ex. largeur
en m) en plus du nom, et comment en extraire proprement la largeur.
"""

import json
import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses/barres-de-coupe-varifeed-pour-moissonneuses-batteuses"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        try:
            accept = page.locator("#onetrust-accept-btn-handler")
            if accept.is_visible(timeout=3000):
                accept.click(timeout=3000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        clicks = 0
        for _ in range(10):
            try:
                btn = page.get_by_text("VOIR PLUS DE MODÈLES", exact=False).first
                if not btn.is_visible(timeout=1500):
                    break
                btn.scroll_into_view_if_needed(timeout=2000)
                btn.click(timeout=2000)
                clicks += 1
                page.wait_for_timeout(1500)
            except Exception:
                break
        log.info(f"clics effectués : {clicks}")

        cards_full = page.evaluate(
            """
            () => {
                const cards = Array.from(document.querySelectorAll('.model-listing__card'));
                return cards.map(c => ({
                    fullText: c.innerText,
                    html: c.innerHTML.slice(0, 1500),
                }));
            }
            """
        )
        for i, c in enumerate(cards_full):
            log.info(f"\n=== Carte {i} ===")
            log.info(f"texte complet:\n{c['fullText']}")

        log.info("\n\n=== HTML de la première carte (1500 chars) ===")
        if cards_full:
            log.info(cards_full[0]["html"])

        browser.close()


if __name__ == "__main__":
    main()
