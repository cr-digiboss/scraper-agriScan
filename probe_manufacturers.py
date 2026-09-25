"""
Script de sondage temporaire — à supprimer après usage.
Vérifie si Fendt et New Holland (qui partagent le même parseur "wide" que
Massey Ferguson) ont le même problème d'orientation de tableau inversée.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect(page, url, label):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception as e:
        log.warning(f"Erreur {url} → {e}")
        return

    tables = page.query_selector_all("table")
    log.info(f"Nombre de tables : {len(tables)}")
    if not tables:
        return
    rows = tables[0].query_selector_all("tr")
    log.info(f"Nombre de lignes dans table[0] : {len(rows)}")
    for i, row in enumerate(rows[:4]):
        cells = row.query_selector_all("td, th")
        values = [scraper.clean(c.inner_text()) for c in cells]
        log.info(f"  ligne {i} ({len(cells)} cellules): {values}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(scraper.FENDT_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        fendt_links = scraper._fendt_product_links(page)
        log.info(f"Fendt : {len(fendt_links)} fiches produit trouvées")
        for url in sorted(fendt_links)[:2]:
            inspect(page, url, "Fendt")

        for base_path in scraper.NEW_HOLLAND_CATEGORIES[:1]:
            page.goto(base_path, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            nh_links = scraper._new_holland_product_links(page, base_path)
            log.info(f"\nNew Holland ({base_path}) : {len(nh_links)} fiches trouvées")
            for url in sorted(nh_links)[:2]:
                inspect(page, url, "New Holland")

        browser.close()


if __name__ == "__main__":
    main()
