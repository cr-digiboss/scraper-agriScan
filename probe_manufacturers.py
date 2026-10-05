"""
Script de sondage temporaire — à supprimer après usage.
Round 3 : catégories identifiées (round 2). On inspecte une fiche
produit représentative par marque pour voir la structure (tableau de
specs classique, ou autre chose).
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

PAGES = {
    "Monosem - NG Plus": "https://www.monosem.com/precision-planters/single-seed-planter/pneumatic-planter/ng-plus-4-4e/",
    "Monosem - Front fertilizer": "https://www.monosem.com/fertilizers/front-fertilizer/",
    "Case IH - tracteurs (categorie)": "https://www.caseih.com/fr-fr/france/produits/tracteurs",
    "Deutz-Fahr - serie 6": "https://www.deutz-fahr.com/fr-fr/tracteurs/serie-6",
    "Same - Virtus": "https://www.same-tractors.com/fr-fr/tracteurs/virtus",
}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        for label, url in PAGES.items():
            log.info(f"\n{'='*70}\n{label} → {url}")
            try:
                resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
                log.info(f"  status: {resp.status if resp else None}")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.info(f"  ERREUR goto: {e}")
                continue

            log.info(f"  URL finale: {page.url}")
            log.info(f"  titre: {page.title()}")

            tables = page.query_selector_all("table")
            log.info(f"  {len(tables)} tables")
            for i, t in enumerate(tables[:3]):
                rows = t.query_selector_all("tr")
                log.info(f"    table {i}: {len(rows)} rows")
                if rows:
                    cells0 = rows[0].query_selector_all("td, th")
                    log.info(f"      row0 ({len(cells0)} cellules): {[c.inner_text().strip()[:30] for c in cells0]}")
                if len(rows) > 1:
                    cells1 = rows[1].query_selector_all("td, th")
                    log.info(f"      row1 ({len(cells1)} cellules): {[c.inner_text().strip()[:30] for c in cells1]}")

            # Pas de table : y a-t-il des liens vers des fiches produit individuelles ?
            if not tables:
                from urllib.parse import urlparse
                hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                base_netloc = urlparse(page.url).netloc
                same_domain = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if urlparse(h).netloc == base_netloc))
                log.info(f"  (pas de table) {len(same_domain)} liens même domaine, échantillon :")
                for h in same_domain[:25]:
                    log.info(f"    {h}")

        browser.close()


if __name__ == "__main__":
    main()
