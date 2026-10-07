"""
Script de sondage temporaire — à supprimer après usage.
[Kverneland] 'Capacity (m³)' a été pris pour un nom de modèle sur la fiche
selfline-4.0-compact : la clé "Model" du scraper générique clé/valeur
(cells[0]=clé, cells[1]=valeur) a stocké "Capacity (m³)" comme valeur.
On inspecte la table brute pour comprendre : table à 3 colonnes (clé |
sous-libellé | valeur) au lieu de 2 ?
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URLS = [
    "https://ien.kverneland.com/bale-choppers/mixer-feeders/selfline-4.0-compact",
    "https://ien.kverneland.com/bale-choppers/mixer-feeders/siloking-selfline-4.0-premium",
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))

        for url in URLS:
            log.info(f"\n{'='*70}\n{url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            tables = page.query_selector_all("table")
            log.info(f"  {len(tables)} tables sur la page")
            for ti, table in enumerate(tables):
                rows = table.query_selector_all("tr")
                log.info(f"  table {ti} : {len(rows)} lignes")
                for row in rows[:15]:
                    cells = row.query_selector_all("td, th")
                    texts = [c.inner_text().strip()[:40] for c in cells]
                    log.info(f"    {len(cells)} cols: {texts}")

        browser.close()


if __name__ == "__main__":
    main()
