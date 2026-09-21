"""
Script de sondage temporaire — à supprimer après usage.
Lot 7, round 4 :
- Valtra : confirmer le pattern (table "tall" par série) sur une 2e série
- Manitou : ouvrir une vraie fiche produit (pas une sous-catégorie)
- Bednar : dernière tentative -> scroll prolongé sur une catégorie plus
  précise pour voir si la grille produits est chargée en différé
- Maschio Gaspardo : dernière tentative -> aller direct sur
  maschiogaspardo.com (le vrai domaine trouvé dans les liens de cookie)
- Grégoire Besson (0/2 tables) et Rabe (mauvais domaine) : abandonnés,
  pas de round supplémentaire.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def dump_tables(page, url, label, scroll_rounds=8, wait_ms=3500):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)
        for _ in range(scroll_rounds):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(400)
        title = page.title()
        log.info(f"  Titre : {title}")
        tables = page.query_selector_all("table")
        log.info(f"  Tables trouvées : {len(tables)}")
        for i, t in enumerate(tables[:2]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i} : {len(rows)} lignes")
            for r_idx, r in enumerate(rows[:4]):
                cells = r.query_selector_all("td, th")
                cell_texts = [c.inner_text().strip() for c in cells]
                log.info(f"    ligne {r_idx} ({len(cells)} cellules) : {cell_texts}")
        if not tables:
            cards = page.query_selector_all("[class*='product' i], [class*='card' i], [class*='model' i]")
            log.info(f"  Éléments 'card'-like (sans table) : {len(cards)}")
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            log.info(f"  Total liens a[href] : {len(hrefs)}")
            for h in [x for x in hrefs if "bednar.com" in x or "maschiogaspardo" in x][:20]:
                log.info(f"    {h}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


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

        dump_tables(page, "https://www.valtra.fr/produits/seriet.html", "Valtra série T (2e série)")
        dump_tables(page, "https://www.manitou.com/fr-FR/nos-machines/chariots-telescopiques/mht-10135-st5", "Manitou fiche produit réelle")
        dump_tables(page, "https://www.bednar.com/fr/dechaumeurs-a-disques/", "Bednar dechaumeurs a disques", scroll_rounds=12, wait_ms=4500)
        dump_tables(page, "https://www.maschiogaspardo.com/fr/", "Maschio Gaspardo (vrai domaine)")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
