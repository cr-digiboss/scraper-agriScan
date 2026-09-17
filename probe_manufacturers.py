"""
Script de sondage temporaire — à supprimer après usage.
Dump cellule par cellule (pas juste inner_text de la ligne complète) du
tableau specs Pöttinger Aerosem M, pour connaître la structure exacte
(nombre de <td> par ligne, cellules vides intercalées ou non) avant
d'écrire un parser dédié. Ne touche pas à la base de données.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

POETTINGER_URL = "https://www.poettinger.at/fr_be/produkte/detail/asemm/aerosem-m-semoirs-pneumatiques-portes"


def probe_pottinger_cells(page):
    log.info(f"\n{'=' * 80}\nPöttinger — dump cellule par cellule — {POETTINGER_URL}\n{'=' * 80}")
    try:
        page.goto(POETTINGER_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(5):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(600)

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")
        for i, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            for j, r in enumerate(rows):
                cells = r.query_selector_all("td, th")
                cell_texts = [c.inner_text().strip().replace(chr(10), " / ") for c in cells]
                log.info(f"    ligne {j} ({len(cells)} cellules) : {cell_texts}")

    except Exception as e:
        log.error(f"Erreur Pöttinger : {e}")


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
        probe_pottinger_cells(page)
        browser.close()


if __name__ == "__main__":
    main()
