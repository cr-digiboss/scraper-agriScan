"""
Script de sondage temporaire — à supprimer après usage.
Lot 1 round 2 : URLs corrigées trouvées via recherche web.
- Horsch : horsch.com/fr-fr a 404, tester horsch.com/fr et la home racine
- Amazone : amazone.fr fonctionne, chercher le lien catalogue produits
- Maschio Gaspardo : bon domaine = maschiogaspardo.com/fr_fr/ (underscore)
- Vicon : bon domaine = fr.vicon.eu (sous-domaine fr.)
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

CANDIDATES = {
    "Horsch": [
        "https://www.horsch.com/fr/",
        "https://www.horsch.com/produkte",
        "https://www.horsch.com/home",
    ],
    "Amazone": [
        "https://www.amazone.fr/",
    ],
    "Maschio Gaspardo": [
        "https://www.maschiogaspardo.com/fr_fr/",
    ],
    "Vicon": [
        "https://fr.vicon.eu/",
    ],
}


def inspect(page, marque, urls):
    for url in urls:
        try:
            resp = page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            status = resp.status if resp else None
            final_url = page.url
            title = page.title()
            log.info(f"\n=== {marque} : {url} -> status={status} final={final_url} title={title!r}")

            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            netloc = urlparse(final_url).netloc
            same_domain = sorted(set(
                h.split("?")[0].split("#")[0] for h in hrefs
                if netloc in urlparse(h).netloc
            ))
            # Filtre : liens contenant des mots-clés catalogue
            mots = ["produit", "product", "gamme", "catalog", "machine", "matériel", "materiel", "range"]
            pertinents = [h for h in same_domain if any(m in h.lower() for m in mots)]
            log.info(f"  {len(same_domain)} liens même domaine, {len(pertinents)} liens 'catalogue' :")
            for h in pertinents[:50]:
                log.info(f"    {h}")
            if status and status < 400:
                return
        except Exception as e:
            log.warning(f"  {marque} : {url} -> échec ({e})")
    log.error(f"  {marque} : AUCUNE URL candidate n'a fonctionné")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for marque, urls in CANDIDATES.items():
            inspect(page, marque, urls)

        browser.close()


if __name__ == "__main__":
    main()
