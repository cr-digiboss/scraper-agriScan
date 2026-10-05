"""
Script de sondage temporaire — à supprimer après usage.
Bug Pöttinger signalé : "il manque plein de modèles". Deux pistes à
vérifier :
1. La page catégorie (ex. Faucheuses) a-t-elle une pagination / bouton
   "voir plus" qui cache des liens produit au-delà du chargement initial ?
2. Une fiche produit a-t-elle PLUSIEURS tables (dont seule tables[0] est
   actuellement exploitée par le scraper), ou un bouton "voir plus de
   modèles" similaire à New Holland ?
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CATEGORY_URL = "https://www.poettinger.at/fr_be/produkte/kategorie/mw/faucheuses"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        log.info(f"=== Page catégorie : {CATEGORY_URL} ===")
        page.goto(CATEGORY_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links_before = sorted(set(h for h in hrefs if "/produkte/detail/" in urlparse(h).path))
        log.info(f"{len(links_before)} liens produit détectés avant interaction")

        # Cherche un bouton "voir plus" / "charger plus" / pagination.
        class_info = page.evaluate(
            """
            () => {
                const keywords = ['load-more', 'pagination', 'show-more', 'mehr', 'plus', 'pager'];
                const found = {};
                keywords.forEach(k => {
                    const els = document.querySelectorAll(`[class*="${k}"]`);
                    if (els.length) {
                        found[k] = Array.from(els).slice(0, 5).map(e => ({cls: e.className, text: e.innerText ? e.innerText.trim().slice(0,40) : ''}));
                    }
                });
                return found;
            }
            """
        )
        log.info(f"classes correspondant à pagination/voir plus : {class_info}")

        # Essaie un scroll complet + clic sur tout bouton texte "plus"/"more"/"charger".
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)

        for text in ["Voir plus", "Charger plus", "Afficher plus", "Load more", "Plus de produits"]:
            try:
                btn = page.get_by_text(text, exact=False).first
                if btn.is_visible(timeout=1000):
                    log.info(f"bouton trouvé et cliqué : {text!r}")
                    btn.click(timeout=2000)
                    page.wait_for_timeout(2000)
            except Exception:
                pass

        hrefs2 = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links_after = sorted(set(h for h in hrefs2 if "/produkte/detail/" in urlparse(h).path))
        log.info(f"{len(links_after)} liens produit détectés après scroll/clic")
        new_links = set(links_after) - set(links_before)
        log.info(f"nouveaux liens apparus : {sorted(new_links)}")

        browser.close()


if __name__ == "__main__":
    main()
