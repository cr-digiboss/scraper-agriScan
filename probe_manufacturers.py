"""
Script de sondage temporaire — à supprimer après usage.
Investigation Fendt (structure de tableau suspecte) et New Holland (0 fiche
produit trouvée sur la catégorie tracteurs).
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

        # ---- Fendt : dump du HTML brut de la table pour comprendre la structure ----
        page.goto(scraper.FENDT_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        fendt_links = scraper._fendt_product_links(page)
        log.info(f"Fendt : {len(fendt_links)} fiches produit trouvées")
        url = sorted(fendt_links)[0]
        log.info(f"\n===== Fendt : {url} =====")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        tables = page.query_selector_all("table")
        log.info(f"Nombre de tables : {len(tables)}")
        if tables:
            html = tables[0].evaluate("el => el.outerHTML")
            log.info(f"HTML brut (2000 premiers caractères) :\n{html[:2000]}")

        # ---- New Holland : vérifier pourquoi 0 lien produit ----
        base_path = scraper.NEW_HOLLAND_CATEGORIES[0]
        log.info(f"\n===== New Holland : {base_path} =====")
        try:
            resp = page.goto(base_path, timeout=30000, wait_until="domcontentloaded")
            log.info(f"Statut HTTP : {resp.status if resp else 'N/A'}")
        except Exception as e:
            log.warning(f"Erreur navigation : {e}")
        page.wait_for_timeout(5000)
        log.info(f"Titre de la page : {page.title()}")
        log.info(f"URL finale : {page.url}")
        all_hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        log.info(f"Nombre total de liens <a> sur la page : {len(all_hrefs)}")
        nh_hrefs = [h for h in all_hrefs if "newholland.com" in h]
        log.info(f"Liens vers newholland.com : {len(nh_hrefs)}")
        for h in sorted(set(nh_hrefs))[:15]:
            log.info(f"  {h}")

        browser.close()


if __name__ == "__main__":
    main()
