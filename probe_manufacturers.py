"""
Script de sondage temporaire — à supprimer après usage.
Güttler, complétude round 2 : récupération du sitemap produits
WooCommerce complet.
"""

import logging
import re

import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    url = "https://guttler.org/wp-sitemap-posts-product-1.xml"
    log.info(f"===== {url} =====")
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    log.info(f"Status : {resp.status_code}")
    log.info(f"Longueur : {len(resp.text)}")
    urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
    log.info(f"Nombre de <loc> : {len(urls)}")

    # regrouper par langue (préfixe de chemin)
    from collections import Counter
    langs = Counter()
    for u in urls:
        path = u.replace("https://guttler.org", "")
        parts = [p for p in path.split("/") if p]
        prefix = parts[0] if parts and len(parts[0]) == 2 else "(racine/DE)"
        langs[prefix] += 1
    log.info(f"Répartition par préfixe : {dict(langs)}")

    fr_urls = sorted(u for u in urls if "/fr/produit/" in u)
    log.info(f"\nURLs françaises (/fr/produit/) : {len(fr_urls)}")
    for u in fr_urls:
        log.info(f"  {u}")

    de_urls = sorted(u for u in urls if "/fr/" not in u and "/en/" not in u and "/nl/" not in u)
    log.info(f"\nURLs allemandes (racine, sans préfixe langue) : {len(de_urls)}")
    for u in de_urls[:60]:
        log.info(f"  {u}")


if __name__ == "__main__":
    main()
