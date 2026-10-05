"""
Script de sondage temporaire — à supprimer après usage.
Bug Kuhn confirmé probable : les 4 doublons viennent de la même URL
source avec des specs quasi identiques. Hypothèse : le site Kuhn a
changé le nom affiché dans l'en-tête du tableau ("6157 TP" ->
"MULTI-LONGER GII EP 6157 TP") entre deux scrapes passés, laissant les
anciennes entrées orphelines. On vérifie le nom actuellement affiché sur
la page live, et on recherche d'autres doublons du même type ailleurs
dans le catalogue Kuhn (même sourceUrl, noms différents).
"""

import logging

from playwright.sync_api import sync_playwright

import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://www.kuhn.fr/paysage-voirie/materiels-dentretien-du-paysage/faucheuses-debroussailleuses/multi-longer-gii"


def check_live_page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        for _ in range(6):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(250)

        tables = page.query_selector_all("table")
        log.info(f"{len(tables)} tables sur la page live")
        for i in range(0, len(tables) - 1, 2):
            data_rows = tables[i + 1].query_selector_all("tr")
            if not data_rows:
                continue
            header_cells = data_rows[0].query_selector_all("td, th")
            header = [c.inner_text().strip() for c in header_cells]
            if any(header):
                log.info(f"  paire {i}: en-tête = {header}")
        browser.close()


def check_other_duplicates():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT "sourceUrl", array_agg(name ORDER BY name) AS names, count(*) AS n
        FROM "Machine"
        WHERE brand = 'Kuhn'
        GROUP BY "sourceUrl"
        HAVING count(*) > 1
        ORDER BY n DESC
        """
    )
    rows = cur.fetchall()
    log.info(f"\n{len(rows)} sourceUrl Kuhn avec plusieurs entrées (doublons potentiels) :")
    for source_url, names, n in rows:
        log.info(f"  [{n}] {source_url}")
        log.info(f"      {names}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    log.info("=== Vérification page live ===")
    check_live_page()
    log.info("\n=== Recherche d'autres doublons (même sourceUrl, plusieurs noms) ===")
    check_other_duplicates()
