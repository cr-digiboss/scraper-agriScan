"""
Script de sondage temporaire — à supprimer après usage.
Massey Ferguson : le nom de la machine ("m.name") ressemble à une spec, pas
à un modèle. Inspection brute de la structure du tableau sur une vraie
fiche produit pour comprendre le format réel.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(scraper.MF_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        links = scraper._mf_product_links(page)
        log.info(f"{len(links)} fiches produit trouvées")
        sample = sorted(links)[:3]

        for url in sample:
            log.info(f"\n===== {url} =====")
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.warning(f"Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            log.info(f"Nombre de tables sur la page : {len(tables)}")
            if not tables:
                continue

            table = tables[0]
            rows = table.query_selector_all("tr")
            log.info(f"Nombre de lignes dans table[0] : {len(rows)}")
            for i, row in enumerate(rows[:6]):
                cells = row.query_selector_all("td, th")
                values = [scraper.clean(c.inner_text()) for c in cells]
                log.info(f"  ligne {i} ({len(cells)} cellules): {values}")

            log.info("Résultat _machines_from_wide_table :")
            machines = scraper._machines_from_wide_table(table, "Massey Ferguson", "Test", "Test", url)
            for m in machines[:5]:
                log.info(f"  name={m.name!r} specs={m.specs[:200]}")

        browser.close()


if __name__ == "__main__":
    main()
