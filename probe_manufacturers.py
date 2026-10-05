"""
Script de sondage temporaire — à supprimer après usage.
Round 5 : structures identifiées round 4 :
- Case IH : des divs "product-card__summary-specs*" directement sur la
  page catégorie tracteurs (plateforme CNH, comme New Holland mais avec
  une nomenclature différente).
- Deutz-Fahr / Same (groupe SDF) : une "table" en divs
  "specifiche-tecniche_wrapper-table__table" (comme Fendt : grille en
  divs, pas de <table> natif).
- Monosem : rien de structuré trouvé — on vérifie le "planter-comparison-
  tool" avant d'abandonner.
On inspecte le détail (HTML) de ces structures.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def dump_html(page, selector, label, limit=2, max_len=2500):
    els = page.query_selector_all(selector)
    log.info(f"  {label} : {len(els)} éléments trouvés pour sélecteur {selector!r}")
    for i, el in enumerate(els[:limit]):
        log.info(f"  --- élément {i} ---")
        log.info(el.evaluate("e => e.outerHTML")[:max_len])


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        log.info(f"\n{'='*70}\nCase IH tracteurs (categorie)")
        page.goto("https://www.caseih.com/fr-fr/france/produits/tracteurs", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        dump_html(page, ".product-card", "cartes produit", limit=2, max_len=3000)

        log.info(f"\n{'='*70}\nDeutz-Fahr serie 6")
        page.goto("https://www.deutz-fahr.com/fr-fr/tracteurs/serie-6", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        dump_html(page, ".specifiche-tecniche_wrapper-table__table", "table specifiche-tecniche", limit=1, max_len=4000)
        dump_html(page, ".specifiche-tecniche_slider", "slider specifiche-tecniche", limit=1, max_len=2000)

        log.info(f"\n{'='*70}\nSame Virtus")
        page.goto("https://www.same-tractors.com/fr-fr/tracteurs/virtus", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        dump_html(page, ".specifiche-tecniche_wrapper-table__table", "table specifiche-tecniche", limit=1, max_len=4000)

        log.info(f"\n{'='*70}\nMonosem planter-comparison-tool")
        try:
            page.goto("https://www.monosem.com/planter-comparison-tool/", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            log.info(f"  titre: {page.title()}")
            n_tables = len(page.query_selector_all("table"))
            log.info(f"  {n_tables} tables")
            body_text = page.inner_text("body")[:1500]
            log.info(f"  texte body (1500 premiers car.) :\n{body_text}")
        except Exception as e:
            log.info(f"  ERREUR: {e}")

        browser.close()


if __name__ == "__main__":
    main()
