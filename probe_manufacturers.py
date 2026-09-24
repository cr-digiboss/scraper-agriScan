"""
Script de sondage temporaire — à supprimer après usage.
Actisol, round 3 : format specs sur une vraie fiche produit
(Demeter et Stellaïr).
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect(page, label, url):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre : {title} — URL finale : {page.url}")
        log.info(f"  Tables : {len(tables)}")
        for i, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"  --- Table {i} ({len(rows)} lignes) ---")
            for row in rows[:10]:
                cells = row.query_selector_all("td, th")
                texts = [c.inner_text().strip().replace("\n", " ") for c in cells]
                log.info("    " + " | ".join(texts))
        divtables = page.query_selector_all("[class*='table' i]")
        log.info(f"  Éléments class*=table : {len(divtables)}")
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

        inspect(page, "Actisol Demeter", "https://actisol-agri.fr/produit/demeter-fissurateur-actisol/")
        inspect(page, "Actisol Stellaïr", "https://actisol-agri.fr/produit/stellair-grande-culture/")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
