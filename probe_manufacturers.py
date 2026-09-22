"""
Script de sondage temporaire — à supprimer après usage.
John Deere, round 3 : catégorie tracteurs -> fiche produit -> table specs.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

CATEGORY_URL = "https://www.deere.fr/fr-fr/produits-et-solutions/tracteurs"


def inspect_product_page(page, url):
    log.info(f"    -> ouverture fiche : {url}")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"       Titre: {title}")
        log.info(f"       Tables trouvées: {len(tables)}")
        for i, t in enumerate(tables[:2]):
            txt = t.inner_text()
            log.info(f"       --- table {i} ({len(txt)} car.) ---")
            log.info("       " + txt[:400].replace("\n", " | "))
        if not tables:
            specish = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], [class*='donnee' i]")
            log.info(f"       Éléments spec-like (sans table): {len(specish)}")
    except Exception as e:
        log.info(f"       ERREUR : {e!r}")


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

        log.info(f"\n===== Catégorie : {CATEGORY_URL} =====")
        try:
            page.goto(CATEGORY_URL, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            for _ in range(8):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(300)
            title = page.title()
            log.info(f"  Titre : {title}")
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            base_path = urlparse(CATEGORY_URL).path
            seen = set()
            candidates = []
            for href in hrefs:
                u = urlparse(href)
                if "deere" not in u.netloc:
                    continue
                clean = href.split("?")[0].split("#")[0]
                if clean in seen or urlparse(clean).path.rstrip("/") == base_path.rstrip("/"):
                    continue
                if not urlparse(clean).path.startswith(base_path):
                    continue
                seen.add(clean)
                candidates.append(clean)
            log.info(f"  Candidats sous-chemin : {len(candidates)}")
            for c in candidates[:20]:
                log.info(f"    {c}")
            if candidates:
                inspect_product_page(page, candidates[0])
                if len(candidates) > 1:
                    inspect_product_page(page, candidates[1])
        except Exception as e:
            log.info(f"  ERREUR : {e!r}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
