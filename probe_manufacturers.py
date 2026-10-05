"""
Script de sondage temporaire — à supprimer après usage.
Lot 8, round 1 : sonde la structure de 4 nouvelles marques demandées
(Monosem, Case IH, Deutz-Fahr, Same) — trouver le site officiel, une page
catalogue/catégorie, des liens produits, puis la structure d'une fiche
produit (tableau de specs ou autre).
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CANDIDATES = {
    "Monosem": "https://www.monosem.com/gammes-de-produits/",
    "Case IH": "https://www.caseih.com/emea/fr-fr/products",
    "Deutz-Fahr": "https://www.deutz-fahr.com/fr-fr/produits",
    "Same": "https://www.same-tractors.com/fr-fr/produits",
}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        for brand, url in CANDIDATES.items():
            log.info(f"\n{'='*70}\n{brand} → {url}")
            try:
                resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
                log.info(f"  status: {resp.status if resp else None}")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.info(f"  ERREUR goto: {e}")
                continue

            log.info(f"  URL finale: {page.url}")
            log.info(f"  titre: {page.title()}")

            # Compte des tableaux et liens sur la page
            n_tables = len(page.query_selector_all("table"))
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            log.info(f"  {n_tables} tables, {len(hrefs)} liens")

            # Quelques liens représentatifs (uniques, même domaine)
            from urllib.parse import urlparse
            base_netloc = urlparse(page.url).netloc
            same_domain = sorted(set(h for h in hrefs if urlparse(h).netloc == base_netloc))
            log.info(f"  échantillon de liens même domaine ({len(same_domain)} uniques) :")
            for h in same_domain[:15]:
                log.info(f"    {h}")

        browser.close()


if __name__ == "__main__":
    main()
