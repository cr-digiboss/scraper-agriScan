"""
Script de sondage temporaire — à supprimer après usage.
Kubota, round 8 (dernier avant écriture du scraper) :
- Vérifier que la structure div.models-table (row thead + row) se
  retrouve identique sur une autre fiche produit (m6002).
- Lister les catégories agriculture disponibles (déjà repérées au
  round 4 : tracteurs-agricoles, tracteurs-specialises, chargeurs-frontaux,
  atomiseur, vehicules-utilitaires, manutention,
  tractor-implement-management, anciens-modeles) et le nombre de liens
  produits par catégorie.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

CATEGORIES = [
    "tracteurs-agricoles",
    "tracteurs-specialises",
    "chargeurs-frontaux",
    "vehicules-utilitaires",
    "manutention",
]


def clean(t):
    return " ".join((t or "").split())


def inspect_models_table(page, url):
    log.info(f"\n===== Kubota produit : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        container = page.query_selector(".models-table")
        if not container:
            log.info("  Pas de .models-table trouvé")
            return
        rows = container.query_selector_all(":scope > .row")
        log.info(f"  Lignes .row : {len(rows)}")
        header = None
        for row in rows:
            cls = row.get_attribute("class") or ""
            cols = row.query_selector_all(":scope > .col")
            if "thead" in cls:
                header = [clean(c.inner_text()) for c in cols]
                log.info(f"  HEADER : {header}")
            else:
                vals = []
                for c in cols:
                    title_el = c.query_selector(".col-title")
                    title_txt = clean(title_el.inner_text()) if title_el else ""
                    full_txt = clean(c.inner_text())
                    if title_txt and full_txt.startswith(title_txt):
                        val = full_txt[len(title_txt):].strip()
                    else:
                        val = full_txt
                    vals.append(val)
                log.info(f"  ROW : {vals}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def list_category_links(page, cat):
    url = f"https://ke.kubota-eu.com/agriculture/fr/product-category/{cat}/"
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(250)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = set()
        for href in hrefs:
            u = urlparse(href)
            if "kubota-eu.com" not in u.netloc:
                continue
            if "/agriculture/fr/products/" not in href:
                continue
            clean_href = href.split("?")[0].split("#")[0]
            if clean_href.rstrip("/").endswith("/products"):
                continue
            seen.add(clean_href)
        log.info(f"  {cat} → {len(seen)} produits : {sorted(seen)}")
    except Exception as e:
        log.info(f"  {cat} → ERREUR : {e!r}")


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

        inspect_models_table(page, "https://ke.kubota-eu.com/agriculture/fr/products/m6002/")

        log.info("\n===== Catégories agriculture Kubota =====")
        for cat in CATEGORIES:
            list_category_links(page, cat)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
