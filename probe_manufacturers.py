"""
Script de sondage temporaire — à supprimer après usage.
Lot 9, round 4 : Horsch et Joskin abandonnés (PDF-only, confirmé sur
2-3 pages chacun). On se concentre sur les 3 marques prometteuses en
extrayant les VRAIS liens (pas des URLs devinées) :
- Merlo : vraie racine catégorie chariots-telescopiques (tous ses liens)
- Monosem : tous les liens internes de la page multicrop (modèle réel ?)
- Pellenc : recherche de liens contenant produit/materiel/gamme
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def dump_links(page, label, url, filter_keywords=None):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        log.info(f"  Titre : {page.title()} — URL finale : {page.url}")
        tables = page.query_selector_all("table")
        log.info(f"  Tables : {len(tables)}")
        divtables = page.query_selector_all("[class*='table' i]")
        log.info(f"  Éléments class*=table : {len(divtables)}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs))
        if filter_keywords:
            seen = [s for s in seen if any(k in s.lower() for k in filter_keywords)]
        log.info(f"  Liens ({'filtrés' if filter_keywords else 'tous'}) : {len(seen)}")
        for s in seen[:60]:
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

        dump_links(page, "Merlo racine chariots-telescopiques",
                   "https://www.merlo.com/fr/fr/p/chariots-telescopiques/")
        dump_links(page, "Monosem multicrop (tous liens)",
                   "https://www.monosem.fr/bineuses/bineuse-agricole/multicrop/")
        dump_links(page, "Pellenc racine (liens produit/materiel/gamme)",
                   "https://www.pellenc.com/fr-fr/",
                   filter_keywords=["produit", "materiel", "matériel", "gamme", "/p/", "catalogue"])

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
