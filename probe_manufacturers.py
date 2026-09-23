"""
Script de sondage temporaire — à supprimer après usage.
Kubota, round 5 :
- Case IH abandonné (round 4) : données uniquement au niveau "gamme"
  (4 attributs génériques, souvent des plages ex. "355-404 ch"), aucun
  modèle individuel exploitable.
- Kubota : vérifier une fiche produit individuelle (m4003) pour voir si
  elle contient un vrai tableau de specs, puis lister les liens produits
  de la catégorie tracteurs-agricoles pour connaître le volume.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect_kubota_product(page, url):
    log.info(f"\n===== Kubota produit : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre : {title}")
        log.info(f"  Tables : {len(tables)}")
        for i, t in enumerate(tables[:5]):
            rows = t.query_selector_all("tr")
            log.info(f"  --- Table {i} ({len(rows)} lignes) ---")
            for row in rows[:6]:
                cells = row.query_selector_all("td, th")
                texts = [c.inner_text().strip().replace("\n", " ") for c in cells]
                log.info("    " + " | ".join(texts))
        # fallback : chercher des blocs de specs hors table
        specish = page.query_selector_all("[class*='spec' i]")
        log.info(f"  Éléments class*=spec : {len(specish)}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def list_kubota_category(page, url):
    log.info(f"\n===== Kubota catégorie : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = set()
        for href in hrefs:
            u = urlparse(href)
            if "kubota-eu.com" not in u.netloc:
                continue
            if "/agriculture/fr/products/" not in href:
                continue
            clean = href.split("?")[0].split("#")[0]
            seen.add(clean)
        log.info(f"  Liens produits uniques : {len(seen)}")
        for s in sorted(seen):
            log.info(f"    {s}")
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

        inspect_kubota_product(page, "https://ke.kubota-eu.com/agriculture/fr/products/m4003/")
        list_kubota_category(page, "https://ke.kubota-eu.com/agriculture/fr/product-category/tracteurs-agricoles/")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
