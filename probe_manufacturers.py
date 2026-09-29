"""
Script de sondage temporaire — à supprimer après usage.
Lot 3 : Hardi, Tecnoma, Agrifac, Lely. Round 1 : trouver la bonne URL FR
pour chacune et lister les liens de navigation pour repérer la page catalogue.
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
    "Hardi": [
        "https://hardi.com/fr",
        "https://www.hardi-fr.com/",
    ],
    "Tecnoma": [
        "https://www.tecnoma.com/produits/pulverisateur-agricoles/pulverisateur-porte/",
        "https://www.tecnoma.com/",
    ],
    "Agrifac": [
        "https://www.agrifac.com/fr/",
        "https://www.agrifac.com/",
    ],
    "Lely": [
        "https://www.lely.com/fr/",
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
            mots = ["produit", "product", "gamme", "catalog", "machine", "pulveris", "sprayer", "robot", "range"]
            pertinents = [h for h in same_domain if any(m in h.lower() for m in mots)]
            log.info(f"  {len(same_domain)} liens même domaine, {len(pertinents)} liens 'catalogue' :")
            for h in pertinents[:40]:
                log.info(f"    {h}")
            if status and status < 400:
                return
        except Exception as e:
            log.warning(f"  {marque} : {url} -> échec ({e})")
    log.error(f"  {marque} : AUCUNE URL candidate n'a fonctionné")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        for marque, urls in CANDIDATES.items():
            inspect(page, marque, urls)

        browser.close()


if __name__ == "__main__":
    main()
