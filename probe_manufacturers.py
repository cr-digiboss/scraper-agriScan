"""
Script de sondage temporaire — à supprimer après usage.
Dump complet des tableaux de specs pour comprendre leur orientation exacte
avant d'écrire le parseur définitif. Ne touche pas à la base de données.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

PAGES = {
    "Kverneland 2300 S Variomat": "https://ien.kverneland.com/ploughs/reversible-ploughs/kverneland-2300-s-variomat",
    "Claas Arion 400": "https://www.claas.com/fr-fr/machines-agricoles/tracteurs/arion-400",
}


def dump_tables(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    for _ in range(6):
        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(600)

    tables = page.query_selector_all("table")
    log.info(f"{len(tables)} table(s) trouvée(s)")
    for ti, t in enumerate(tables):
        rows = t.query_selector_all("tr")
        log.info(f"\n--- Table {ti} : {len(rows)} lignes ---")
        for ri, r in enumerate(rows):
            cells = r.query_selector_all("td, th")
            cell_texts = [c.inner_text().strip().replace("\n", " / ") for c in cells]
            log.info(f"  Ligne {ri} ({len(cells)} cellules) : {cell_texts}")


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
        for name, url in PAGES.items():
            try:
                dump_tables(name, url, page)
            except Exception as e:
                log.error(f"Erreur sur {name} : {e}")
        browser.close()


if __name__ == "__main__":
    main()
