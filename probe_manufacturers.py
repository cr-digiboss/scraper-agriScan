"""
Script de sondage temporaire — à supprimer après usage.
Confirme que la découverte des liens produit McHale fonctionne aussi
en HTTP simple (sans navigateur), avant de réécrire scrape_mchale.
"""

import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

MCHALE_HOME = "https://www.mchale.net/"


def main():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }
    resp = requests.get(MCHALE_HOME, headers=headers, timeout=30)
    log.info(f"HTTP status home : {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(MCHALE_HOME, a["href"])
        u = urlparse(href)
        if "mchale.net" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 2 and segments[0] == "products":
            links.add(href.split("?")[0].split("#")[0])

    log.info(f"Liens produit trouvés : {len(links)}")
    for l in sorted(links)[:10]:
        log.info(f"  {l}")

    # Vérifie une deuxième fiche produit au hasard pour confirmer que ce
    # n'est pas spécifique à la page 691 déjà testée.
    if len(links) >= 2:
        second_url = sorted(links)[5] if len(links) > 5 else sorted(links)[1]
        resp2 = requests.get(second_url, headers=headers, timeout=30)
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        tables2 = soup2.find_all("table")
        log.info(f"Deuxième fiche testée : {second_url}")
        log.info(f"  HTTP status : {resp2.status_code}, tables trouvées : {len(tables2)}")
        if tables2:
            rows = tables2[0].find_all("tr")
            log.info(f"  Lignes dans la première table : {len(rows)}")
            for r in rows[:5]:
                cells = r.find_all("td")
                log.info(f"    {[c.get_text(strip=True) for c in cells]}")


if __name__ == "__main__":
    main()
