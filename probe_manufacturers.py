"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland round 2 : cliquer sur "VOIR PLUS DE MODÈLES" (répéter
jusqu'à disparition) et vérifier que le tableau de specs s'enrichit de
colonnes supplémentaires.
"""

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

        def table_header():
            tables = page.query_selector_all("table")
            if not tables:
                return None, 0
            rows = tables[0].query_selector_all("tr")
            if not rows:
                return None, 0
            cells = rows[0].query_selector_all("td, th")
            return [c.inner_text().strip()[:25] for c in cells], len(rows)

        header, nrows = table_header()
        log.info(f"AVANT clic : {len(header) if header else 0} colonnes, {nrows} rows")
        log.info(f"  header : {header}")

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
            except Exception as e:
                log.info(f"  arrêt clic : {e}")
                break

        log.info(f"\nclics 'VOIR PLUS DE MODÈLES' effectués : {clicks}")
        header, nrows = table_header()
        log.info(f"APRÈS clic(s) : {len(header) if header else 0} colonnes, {nrows} rows")
        log.info(f"  header : {header}")

        browser.close()


if __name__ == "__main__":
    main()
