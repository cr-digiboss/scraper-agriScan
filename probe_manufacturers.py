"""
Script de sondage temporaire — à supprimer après usage.
Lot 8, round 2 :
- Rauch, Lely, Same : ouvrir une vraie fiche produit et chercher une table
- Sulky : connexion refusée au round 1 -> essayer d'autres URLs/domaines
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect_product_page(page, url, label):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre: {title}")
        log.info(f"  Tables trouvées: {len(tables)}")
        for i, t in enumerate(tables[:2]):
            txt = t.inner_text()
            log.info(f"  --- table {i} ({len(txt)} car.) ---")
            log.info("  " + txt[:400].replace("\n", " | "))
        if not tables:
            specish = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], [class*='donnee' i]")
            log.info(f"  Éléments spec-like (sans table): {len(specish)}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def try_url(page, url, label):
    log.info(f"\n===== {label} (retry) : {url} =====")
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        title = page.title()
        log.info(f"  Titre : {title}")
        log.info(f"  Longueur HTML : {len(page.content())}")
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

        inspect_product_page(page, "https://rauch.de/duengerstreuer/scheibenstreuer/axent.html", "Rauch")
        inspect_product_page(page, "https://www.lely.com/fr/solutions/traite/astronaut/", "Lely")
        inspect_product_page(page, "https://www.same-tractors.com/en-gb/tractors/virtus", "Same")

        try_url(page, "https://www.sulky-burel.com/", "Sulky racine https")
        try_url(page, "http://www.sulky-burel.com/", "Sulky racine http")
        try_url(page, "https://sulky-burel.com/", "Sulky sans www")
        try_url(page, "https://www.sulky.fr/", "Sulky domaine alternatif")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
