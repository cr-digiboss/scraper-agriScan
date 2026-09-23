"""
Script de sondage temporaire — à supprimer après usage.
Lot 9, round 3 :
- Horsch : vérifier une page "campagne" (joker-ct) pour un vrai tableau
  de specs, sinon confirmer PDF-only.
- Merlo : trouver la bonne URL produit depuis la catégorie compacts.
- Monosem : fiche modèle bineuse multicrop.
- Pellenc : trouver la section produits/matériels réelle.
- Joskin : chercher une fiche produit individuelle (pas juste la
  catégorie), ex. via un lien direct type xtrem2/cobra2.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect(page, label, url):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre : {title} — URL finale : {page.url}")
        log.info(f"  Tables : {len(tables)}")
        for i, t in enumerate(tables[:2]):
            rows = t.query_selector_all("tr")
            log.info(f"  --- Table {i} ({len(rows)} lignes) ---")
            for row in rows[:6]:
                cells = row.query_selector_all("td, th")
                texts = [c.inner_text().strip().replace("\n", " ") for c in cells]
                log.info("    " + " | ".join(texts))
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs))
        log.info(f"  Liens uniques : {len(seen)} (25 premiers)")
        for s in seen[:25]:
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

        inspect(page, "Horsch joker-ct", "https://www.horsch.com/fr/dechaumage-rapide-economique-porte/campagne-joker-ct")
        inspect(page, "Merlo compacts", "https://www.merlo.com/fr/fr/p/chariots-telescopiques/chariots-telescopiques-compacts/")
        inspect(page, "Monosem multicrop", "https://www.monosem.fr/bineuses/bineuse-agricole/multicrop/")
        inspect(page, "Pellenc conseils arboriculture", "https://www.pellenc.com/fr-fr/conseils-et-ingenierie/arboriculture")
        inspect(page, "Joskin xtrem2 direct", "https://www.joskin.com/fr/xtrem2")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
