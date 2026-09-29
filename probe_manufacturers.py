"""
Script de sondage temporaire — à supprimer après usage.
Lot 1 de marques manquantes signalées par l'utilisateur : Horsch, Amazone,
Maschio Gaspardo, Vicon. Round 1 : trouver la bonne URL d'accueil FR pour
chacune et lister les liens de navigation pour repérer la page catalogue.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

CANDIDATES = {
    "Horsch": [
        "https://www.horsch.com/fr-fr/",
        "https://www.horsch.com/fr/",
        "https://www.horsch.com/",
    ],
    "Amazone": [
        "https://www.amazone.fr/",
        "https://www.amazone.de/fr/",
    ],
    "Maschio Gaspardo": [
        "https://www.maschionet.com/fr-fr/",
        "https://www.maschio.com/fr/",
        "https://www.maschionet.com/",
    ],
    "Vicon": [
        "https://www.vicon-agriculture.com/fr-fr/",
        "https://www.vicon-agriculture.com/fr/",
        "https://www.vicon-agriculture.com/",
    ],
}


def inspect(page, marque, urls):
    for url in urls:
        try:
            resp = page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
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
            log.info(f"  {len(same_domain)} liens même domaine, échantillon :")
            for h in same_domain[:40]:
                log.info(f"    {h}")
            return  # une URL qui marche suffit
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
