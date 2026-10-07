"""
Script de sondage temporaire — à supprimer après usage.
Le fix Kverneland précédent a créé ~20 fausses "machines" dont le nom est
en fait un nom de fonctionnalité/option (ELDOS, Seed rate adjustment...),
toutes créées à 10:07:48 lors du run #75. On récupère le sourceUrl exact
de ces lignes, puis on inspecte la table brute de la page pour comprendre
pourquoi mon heuristique "header[0] == 'model'" s'est trompée ici.
"""

import logging
import os

import psycopg2
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
        """SELECT DISTINCT "sourceUrl" FROM "Machine"
           WHERE brand = 'Kverneland' AND "createdAt" = '2026-10-07 10:07:48.534000'"""
    )
    urls = [r[0] for r in cur.fetchall()]
    log.info(f"{len(urls)} sourceUrl distincts pour ce lot : {urls}")
    cur.close()
    conn.close()

    if not urls:
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))
        for url in urls:
            log.info(f"\n{'='*70}\n{url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            tables = page.query_selector_all("table")
            log.info(f"  {len(tables)} tables")
            for ti, table in enumerate(tables):
                rows = table.query_selector_all("tr")
                log.info(f"  table {ti} : {len(rows)} lignes")
                for row in rows[:8]:
                    cells = row.query_selector_all("td, th")
                    texts = [c.inner_text().strip()[:35] for c in cells]
                    log.info(f"    {len(cells)} cols: {texts}")
        browser.close()


if __name__ == "__main__":
    main()
