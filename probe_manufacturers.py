"""
Script de sondage temporaire — à supprimer après usage.
Round 4 : aucune <table> trouvée round 3. Hypothèse : Case IH (CNH
Industrial, comme New Holland) et Deutz-Fahr/Same (groupe SDF) partagent
probablement un gabarit similaire à New Holland (onglets Vue d'ensemble/
Modèles/Spécifications, cartes model-listing chargées en JS). On
recherche des classes similaires, et on imprime la liste COMPLETE des
liens (pas tronquée à 25) pour la categorie Case IH tracteurs.
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

PAGES = {
    "Case IH - tracteurs (categorie)": "https://www.caseih.com/fr-fr/france/produits/tracteurs",
    "Deutz-Fahr - serie 6": "https://www.deutz-fahr.com/fr-fr/tracteurs/serie-6",
    "Same - Virtus": "https://www.same-tractors.com/fr-fr/tracteurs/virtus",
    "Monosem - fiche technique NG Plus": "https://www.monosem.com/fiche-technique/ng-plus-ng-plus-e/",
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
                page.wait_for_timeout(5000)
            except Exception as e:
                log.info(f"  ERREUR goto: {e}")
                continue

            log.info(f"  URL finale: {page.url}")
            log.info(f"  titre: {page.title()}")

            n_tables = len(page.query_selector_all("table"))
            log.info(f"  {n_tables} tables")

            # Classes évoquant une structure de specs / listing de modèles
            class_info = page.evaluate(
                """
                () => {
                    const keywords = ['spec', 'model-listing', 'techdata', 'model-detail', 'caracteristique', 'datasheet', 'tab'];
                    const found = {};
                    keywords.forEach(k => {
                        const els = document.querySelectorAll(`[class*="${k}"]`);
                        if (els.length) {
                            found[k] = {
                                count: els.length,
                                sample: Array.from(els).slice(0, 5).map(e => e.className),
                            };
                        }
                    });
                    return found;
                }
                """
            )
            log.info(f"  classes correspondantes : {class_info}")

            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            base_netloc = urlparse(page.url).netloc
            same_domain = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if urlparse(h).netloc == base_netloc))
            log.info(f"  {len(same_domain)} liens uniques même domaine (liste complète) :")
            for h in same_domain:
                log.info(f"    {h}")

        browser.close()


if __name__ == "__main__":
    main()
