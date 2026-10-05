"""
Script de sondage temporaire — à supprimer après usage.
Round 6 :
- Case IH : la carte "Gamme Magnum" dit "se décline en 6 modèles au
  total" mais n'a que des specs agrégées (plage de puissance). On visite
  la page de la gamme pour voir si le détail par modèle y est.
- Deutz-Fahr/Same : le conteneur ".specifiche-tecniche_wrapper-table__
  table" est vide après 5s d'attente (SPA Vue.js, attribut data-v-*
  observé). On clique sur un onglet "Spécifications" si présent et on
  attend plus longtemps avant de re-vérifier.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        log.info(f"\n{'='*70}\nCase IH - gamme Magnum (sous-page)")
        page.goto("https://www.caseih.com/fr-fr/france/produits/tracteurs/magnum-serie", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        log.info(f"  titre: {page.title()}")
        cards = page.query_selector_all(".product-card")
        log.info(f"  {len(cards)} .product-card trouvées")
        for i, c in enumerate(cards[:8]):
            title_el = c.query_selector(".product-card__title")
            log.info(f"    carte {i}: {title_el.inner_text().strip() if title_el else '(pas de titre)'}")
        n_tables = len(page.query_selector_all("table"))
        log.info(f"  {n_tables} tables")

        log.info(f"\n{'='*70}\nSame Virtus - clic onglet Specifications")
        page.goto("https://www.same-tractors.com/fr-fr/tracteurs/virtus", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        try:
            for text in ["Spécifications", "SPÉCIFICATIONS", "Specifiche", "Caractéristiques techniques"]:
                btn = page.get_by_text(text, exact=False).first
                if btn.is_visible(timeout=1500):
                    log.info(f"  onglet trouvé : {text!r}, clic...")
                    btn.scroll_into_view_if_needed(timeout=2000)
                    btn.click(timeout=2000)
                    break
        except Exception as e:
            log.info(f"  pas d'onglet cliquable trouvé : {e}")
        page.wait_for_timeout(4000)
        wrapper = page.query_selector(".specifiche-tecniche_wrapper-table__table")
        log.info(f"  wrapper présent : {wrapper is not None}")
        if wrapper:
            html = wrapper.evaluate("e => e.outerHTML")
            log.info(f"  longueur HTML : {len(html)}")
            log.info(html[:4000])

        browser.close()


if __name__ == "__main__":
    main()
