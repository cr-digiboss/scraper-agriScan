"""
Script de sondage temporaire — à supprimer après usage.
Round 2 : round 1 a donné des pages d'accueil/404 sans liens produits
clairs dans l'échantillon tronqué. On repart des homepages et on imprime
TOUS les liens même domaine pour repérer les vraies URLs de catégories.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CANDIDATES = {
    "Monosem": "https://www.monosem.com/",
    "Case IH": "https://www.caseih.com/fr-fr/france/products",
    "Deutz-Fahr": "https://www.deutz-fahr.com/fr-fr/",
    "Same": "https://www.same-tractors.com/fr-fr/",
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

            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            base_netloc = urlparse(page.url).netloc
            same_domain = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if urlparse(h).netloc == base_netloc))
            log.info(f"  {len(same_domain)} liens uniques même domaine :")
            for h in same_domain:
                log.info(f"    {h}")

        browser.close()


if __name__ == "__main__":
    main()
