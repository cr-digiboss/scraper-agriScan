"""
Script de sondage temporaire — à supprimer après usage.
Test rapide du nouveau parseur texte de _horsch_facts() sur plusieurs
fiches avant de relancer le crawl complet (coûteux).
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        for url in [
            "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques/joker-4-6-hd",
            "https://www.horsch.com/fr/produits/semis/semoir-a-disques/pronto-as",
            "https://www.horsch.com/fr/produits/technique-de-semis-monograine/maestro/maestro-ax",
            "https://www.horsch.com/fr/produits/travail-du-sol",  # catégorie, doit donner {}
        ]:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            specs = scraper._horsch_facts(page)
            log.info(f"{url}\n  -> {len(specs)} specs : {specs}\n")

        browser.close()


if __name__ == "__main__":
    main()
