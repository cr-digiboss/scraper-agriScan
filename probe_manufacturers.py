"""
Script de sondage temporaire — à supprimer après usage.
Case IH round modeles-1 : l'utilisateur demande si on peut récupérer les
vrais modèles individuels plutôt que des gammes agrégées. La sous-page
"Gamme Magnum" n'avait ni carte ni tableau (sondage précédent) — on
regarde ici en détail cette page (tous les liens, PDF, sections) pour
trouver une source de données par modèle (brochure PDF, configurateur,
etc.).
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

URL = "https://www.caseih.com/fr-fr/france/produits/tracteurs/magnum-serie"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        log.info(f"titre: {page.title()}")

        # Tous les liens, y compris PDF
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        base_netloc = urlparse(page.url).netloc
        same_domain = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if urlparse(h).netloc == base_netloc))
        log.info(f"\n{len(same_domain)} liens même domaine :")
        for h in same_domain:
            log.info(f"  {h}")

        pdfs = [h for h in hrefs if h.lower().endswith(".pdf")]
        log.info(f"\n{len(pdfs)} liens PDF :")
        for h in pdfs:
            log.info(f"  {h}")

        # Classes évoquant un configurateur, un sélecteur de modèle, ou une
        # liste de modèles au sein de la gamme.
        class_info = page.evaluate(
            """
            () => {
                const keywords = ['model', 'configurat', 'compare', 'spec', 'select', 'variant'];
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
        log.info(f"\nclasses correspondantes : {class_info}")

        # Texte intégral de la page pour repérer toute mention de modèles
        # individuels (ex. "Magnum 340", "Magnum 380"...).
        body_text = page.inner_text("body")
        log.info(f"\ntaille texte body : {len(body_text)}")
        log.info(body_text[:3000])

        browser.close()


if __name__ == "__main__":
    main()
