"""
Script de sondage temporaire — à supprimer après usage.
Bug Kuhn : l'utilisateur signale 2 paires de doublons dans le catalogue :
"6157 TP" / "6157 TP PWR" (catégorie "Autre", pas d'image) vs
"MULTI-LONGER GII EP 6157 TP" / "MULTI-LONGER GII EP 6157 TP PWR"
(catégorie "Broyage & Débroussaillage", avec image). On cherche les
pages produit Kuhn correspondantes pour comprendre l'origine exacte
(une page avec plusieurs paires de tables ? deux URLs distinctes ?).
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

CATEGORIES = {
    "Broyage grande culture": "https://www.kuhn.fr/grande-culture/broyeurs",
    "Broyage polyvalent": "https://www.kuhn.fr/herbe-fourrages/broyeurs-polyvalents",
    "Broyage paysage": "https://www.kuhn.fr/paysage-voirie/broyeurs",
}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        for cat_name, cat_url in CATEGORIES.items():
            log.info(f"\n{'='*70}\n{cat_name} → {cat_url}")
            page.goto(cat_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            matches = sorted(set(h for h in hrefs if "6157" in h.lower() or "multi-longer" in h.lower()))
            log.info(f"  liens correspondant à '6157' ou 'multi-longer' : {matches}")

        browser.close()


if __name__ == "__main__":
    main()
