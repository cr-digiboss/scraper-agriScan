"""
Script de sondage temporaire — à supprimer après usage.
John Deere, round 4 : "tracteurs-compacts" est encore une catégorie
(0 table) -> descendre un niveau de plus pour trouver la vraie fiche
modèle avec un tableau de specs.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

CATEGORY_URL = "https://www.deere.fr/fr-fr/produits-et-solutions/tracteurs/tracteurs-compacts"


def inspect(page, url, depth=0):
    prefix = "  " * (depth + 1)
    log.info(f"{prefix}-> ouverture : {url}")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"{prefix}   Titre: {title} | Tables: {len(tables)}")
        if tables:
            txt = tables[0].inner_text()
            log.info(f"{prefix}   --- table 0 ({len(txt)} car.) ---")
            log.info(f"{prefix}   " + txt[:400].replace("\n", " | "))
        return url
    except Exception as e:
        log.info(f"{prefix}   ERREUR : {e!r}")
        return None


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

        log.info(f"\n===== Sous-catégorie : {CATEGORY_URL} =====")
        page.goto(CATEGORY_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        log.info(f"  Titre : {title}")

        base_path = urlparse(CATEGORY_URL).path
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
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

        for c in candidates[:3]:
            inspect(page, c)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
