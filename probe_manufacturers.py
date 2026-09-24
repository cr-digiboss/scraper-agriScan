"""
Script de sondage temporaire — à supprimer après usage.
Güttler, complétude : la catégorie française (/fr/produits/) ne liste
que 12 fiches, alors que le site allemand a 10 catégories (Prismenwalze,
Packerwalzen, Stoppelbearbeitung, Obst-und-Weinbau, etc.) probablement
plus riches. Recherche d'un sitemap XML pour découvrir TOUTES les
vraies pages produit du site, langue par langue.
"""

import logging
import re

import requests
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

SITEMAP_CANDIDATES = [
    "https://guttler.org/sitemap.xml",
    "https://guttler.org/sitemap_index.xml",
    "https://guttler.org/wp-sitemap.xml",
    "https://guttler.org/product-sitemap.xml",
    "https://guttler.org/produkt-sitemap.xml",
]


def try_sitemap(url):
    log.info(f"\n===== Sitemap : {url} =====")
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        log.info(f"  Status : {resp.status_code}")
        if resp.status_code == 200:
            log.info(f"  Longueur : {len(resp.text)}")
            log.info("  Extrait (1500 premiers car.) :")
            log.info("  " + resp.text[:1500].replace("\n", " "))
            urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
            log.info(f"  Nombre de <loc> : {len(urls)}")
            for u in urls[:40]:
                log.info(f"    {u}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def main():
    for url in SITEMAP_CANDIDATES:
        try_sitemap(url)


if __name__ == "__main__":
    main()
