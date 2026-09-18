"""
Script de sondage temporaire — à supprimer après usage.
Lot 5, round 3 : vérifie la structure des tableaux de specs sur de
vraies fiches produit Lemken, Horsch et Vicon trouvées au round 2.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URLS = {
    "Lemken (Juwel 7)": "https://lemken.com/fr-fr/machines-agricoles/travail-du-sol/labour/charrues-portees/juwel-7",
    "Horsch (Joker RT)": "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques/joker-rt",
    "Vicon (Bromex PA)": "https://ien.vicon.eu/choppers/flail-choppers/vicon-bromex-pa",
}


def probe(page, name, url):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=25000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(4000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(400)

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")
        for i, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            for r in rows[:6]:
                log.info(f"    {r.inner_text().replace(chr(10), ' | ')[:180]}")

        spec_els = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='daten' i]")
        log.info(f"Éléments [class*=spec/technical/daten] : {len(spec_els)}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


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
        for name, url in URLS.items():
            probe(page, name, url)
        browser.close()


if __name__ == "__main__":
    main()
