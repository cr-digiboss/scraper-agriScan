"""
Script de sondage temporaire — à supprimer après usage.
Round 2 : pas de pagination manquante sur la page catégorie Faucheuses
(13 liens, stable après scroll/clic). On regarde maintenant une fiche
produit individuelle : combien de <table> au total (le scraper
n'utilise que tables[0]), et s'il y a un bouton "voir plus de modèles"
caché (comme New Holland).
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CATEGORY_URL = "https://www.poettinger.at/fr_be/produkte/kategorie/mw/faucheuses"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        page.goto(CATEGORY_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        hrefs = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href).filter(h => h.includes('/produkte/detail/'))"
        )
        links = sorted(set(hrefs))
        log.info(f"{len(links)} fiches produit dans Faucheuses :")
        for h in links:
            log.info(f"  {h}")

        # Inspecte les 3 premières fiches en détail.
        for url in links[:3]:
            log.info(f"\n{'='*70}\n{url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            for _ in range(6):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(250)

            tables = page.query_selector_all("table")
            log.info(f"  {len(tables)} tables sur la page")
            for i, t in enumerate(tables):
                rows = t.query_selector_all("tr")
                if rows:
                    cells0 = rows[0].query_selector_all("td, th")
                    header = [c.inner_text().strip()[:25] for c in cells0]
                    log.info(f"    table {i}: {len(rows)} rows, en-tête={header}")

            # Boutons "voir plus" / sélecteurs de modèles sur la fiche.
            class_info = page.evaluate(
                """
                () => {
                    const keywords = ['model', 'variant', 'show-more', 'load-more', 'mehr'];
                    const found = {};
                    keywords.forEach(k => {
                        const els = document.querySelectorAll(`[class*="${k}"]`);
                        if (els.length) found[k] = els.length;
                    });
                    return found;
                }
                """
            )
            log.info(f"  classes correspondantes : {class_info}")

        browser.close()


if __name__ == "__main__":
    main()
