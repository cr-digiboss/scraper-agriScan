"""
Script de sondage temporaire — à supprimer après usage.
John Deere, round 6 : vraies fiches modèles trouvées sous
/produits-solutions/tracteurs/tracteurs-compacts/<slug> -> vérifier la
présence et le format d'un tableau de specs sur 2 fiches.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URLS = [
    "https://www.deere.fr/fr-fr/produits-solutions/tracteurs/tracteurs-compacts/2032r-tracteur-compact-mtuzmurn",
    "https://www.deere.fr/fr-fr/produits-solutions/tracteurs/tracteurs-compacts/4052r-tracteur-compact-mdm2q0rn",
]


def inspect(page, url):
    log.info(f"\n===== {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre : {title}")
        log.info(f"  Tables trouvées : {len(tables)}")
        for i, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i} : {len(rows)} lignes")
            for r_idx, r in enumerate(rows[:4]):
                cells = r.query_selector_all("td, th")
                cell_texts = [c.inner_text().strip() for c in cells]
                log.info(f"    ligne {r_idx} ({len(cells)} cellules) : {cell_texts}")
        if not tables:
            specish = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], [class*='donnee' i]")
            log.info(f"  Éléments spec-like (sans table) : {len(specish)}")
            for i, el in enumerate(specish[:5]):
                cls = el.get_attribute("class") or ""
                txt = el.inner_text()
                log.info(f"  --- elt {i} class=\"{cls}\" ({len(txt)} car.) ---")
                log.info("  " + txt[:400].replace("\n", " | "))
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
        for url in URLS:
            inspect(page, url)
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
