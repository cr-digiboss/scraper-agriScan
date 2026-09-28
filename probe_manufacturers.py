"""
Script de sondage temporaire — à supprimer après usage.
Round 2 : catégories McCormick (produits.html?category=X) pour trouver
les liens produit, et inspection d'une fiche produit de chaque marque.
"""

import logging

from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

MCCORMICK_CATEGORIES = [
    "https://mccormick-tractors.com/fr/fr/produits.html?category=chargeurs",
    "https://mccormick-tractors.com/fr/fr/produits.html?category=chenillards",
    "https://mccormick-tractors.com/fr/fr/produits.html?category=grandes+cultures",
    "https://mccormick-tractors.com/fr/fr/produits.html?category=sp%C3%A9cialis%C3%A9s",
    "https://mccormick-tractors.com/fr/fr/produits.html?category=utilitaires",
]

MCCORMICK_SAMPLE_PRODUCT = "https://mccormick-tractors.com/fr/fr/produits/x8-vt-drive.html"
FRANQUET_SAMPLE_PRODUCT = "https://www.franquet.com/desherbage-mecanique/bineuses/"


def inspect_product(page, url, label):
    log.info(f"\n===== Fiche produit {label} : {url} =====")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
    except Exception as e:
        log.warning(f"Erreur : {e}")
        return
    page.wait_for_timeout(4000)
    for _ in range(8):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(300)

    log.info(f"Titre : {page.title()}")
    tables = page.query_selector_all("table")
    log.info(f"Nombre de tables : {len(tables)}")
    for i, table in enumerate(tables[:3]):
        rows = table.query_selector_all("tr")
        log.info(f"  Table {i} : {len(rows)} lignes")
        for r in rows[:4]:
            cells = r.query_selector_all("td, th")
            values = [c.inner_text().strip()[:40] for c in cells]
            log.info(f"    {values}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        log.info("===== Catégories McCormick =====")
        all_products = set()
        for cat_url in MCCORMICK_CATEGORIES:
            try:
                page.goto(cat_url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                log.warning(f"Erreur {cat_url} → {e}")
                continue
            page.wait_for_timeout(3000)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            produits = sorted(set(
                h for h in hrefs
                if "/fr/fr/produits/" in h and h.endswith(".html")
            ))
            log.info(f"{cat_url} → {len(produits)} fiches produit")
            for h in produits:
                log.info(f"  {h}")
            all_products |= set(produits)
        log.info(f"\nTotal fiches produit uniques McCormick (toutes catégories) : {len(all_products)}")

        inspect_product(page, MCCORMICK_SAMPLE_PRODUCT, "McCormick")
        inspect_product(page, FRANQUET_SAMPLE_PRODUCT, "Franquet")

        browser.close()


if __name__ == "__main__":
    main()
