"""
Script de sondage temporaire — à supprimer après usage.
Lot 6, round 4 : confirmer le pattern Kuhn (2 tables : labels + données)
sur 2 fiches supplémentaires de catégories différentes, avec comptage
exact des lignes de chaque table (pour valider le zip labels/valeurs).
Amazone abandonné (specs uniquement en PDF téléchargeable, pas de HTML).
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URLS = [
    "https://www.kuhn.fr/grande-culture/semoirs",
    "https://www.kuhn.fr/herbe-fourrages/presses",
]


def find_first_product(page, url):
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    from urllib.parse import urlparse
    base_path = urlparse(url).path
    seen = set()
    candidates = []
    for href in hrefs:
        u = urlparse(href)
        if "kuhn.fr" not in u.netloc:
            continue
        clean = href.split("?")[0].split("#")[0]
        if clean in seen or u.path == base_path or not u.path.startswith(base_path):
            continue
        seen.add(clean)
        # on veut un lien "profond" (probable fiche produit), pas juste une sous-catégorie
        if u.path.count("/") >= base_path.count("/") + 2:
            candidates.append(clean)
    return candidates


def inspect(page, url):
    log.info(f"\n===== Fiche : {url} =====")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        for _ in range(6):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre : {title}")
        log.info(f"  Nombre de tables : {len(tables)}")
        for i, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i} : {len(rows)} lignes")
            for r_idx, r in enumerate(rows[:3]):
                cells = r.query_selector_all("td, th")
                cell_texts = [c.inner_text().strip() for c in cells]
                log.info(f"    ligne {r_idx} ({len(cells)} cellules) : {cell_texts}")
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

        for cat_url in URLS:
            log.info(f"\n### Catégorie : {cat_url}")
            try:
                candidates = find_first_product(page, cat_url)
                log.info(f"  Candidats profonds trouvés : {len(candidates)}")
                for c in candidates[:5]:
                    log.info(f"    {c}")
                if candidates:
                    inspect(page, candidates[0])
            except Exception as e:
                log.info(f"  ERREUR catégorie : {e!r}")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
