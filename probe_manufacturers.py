"""
Script de sondage temporaire — à supprimer après usage.
Le blocage Playwright ressemble à une détection anti-bot basée sur les
requêtes successives (scroll, viewport, délai : rien n'a marché). Teste
si une simple requête HTTP (requests + BeautifulSoup, sans navigateur)
suffit à récupérer le bloc "Technical Specification" — plausible si le
contenu est en fait rendu côté serveur et non injecté par JS après coup.
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URL = "https://www.mchale.net/products/691-round-bale-handler/"


def main():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }
    resp = requests.get(URL, headers=headers, timeout=30)
    log.info(f"HTTP status : {resp.status_code}")
    log.info(f"Longueur réponse : {len(resp.text)} caractères")

    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    log.info(f"Nombre de <table> : {len(tables)}")

    spec_els = soup.select("[class*='spec' i], [class*='technical' i]")
    log.info(f"Éléments [class*=spec/technical] : {len(spec_els)}")
    for el in spec_els[:5]:
        log.info(f"  <{el.name} class=\"{el.get('class')}\"> {el.get_text()[:200]!r}")

    has_techspec_text = "Technical Specification" in resp.text
    log.info(f"Texte 'Technical Specification' présent dans le HTML brut : {has_techspec_text}")

    has_weight_row = bool(re.search(r"Weight\s*.{0,50}kg", resp.text))
    log.info(f"Motif 'Weight ... kg' présent : {has_weight_row}")

    # Dump d'un extrait autour de "Technical" si trouvé, pour voir le format brut
    idx = resp.text.find("Technical Specification")
    if idx != -1:
        log.info("--- Extrait HTML brut autour de 'Technical Specification' ---")
        log.info(resp.text[idx:idx + 1500])


if __name__ == "__main__":
    main()
