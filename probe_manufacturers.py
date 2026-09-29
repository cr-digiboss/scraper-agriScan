"""
Script de sondage temporaire — à supprimer après usage.
Debug scrape_horsch() : le crawl BFS retourne 0 machine malgré le fix du
filtre de profondeur. Tester _horsch_facts() directement sur une fiche
connue pour fonctionner (joker-4-6-hd) et vérifier le crawl étape par étape.
"""

import logging
from urllib.parse import urlparse

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

        url = "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques/joker-4-6-hd"
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        log.info(f"=== Test direct _horsch_facts() sur {url} ===")
        specs = scraper._horsch_facts(page)
        log.info(f"  specs trouvées : {specs}")

        # Vérifier la home /fr/produits : combien de liens produits (5 segments) trouve-t-on direct ?
        page.goto(scraper.HORSCH_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        log.info(f"\n=== Home {scraper.HORSCH_HOME} : {len(hrefs)} hrefs bruts ===")
        produits_links = set()
        for href in hrefs:
            u = urlparse(href)
            if "horsch.com" not in u.netloc or "/fr/produits/" not in u.path:
                continue
            clean_href = href.split("?")[0].split("#")[0]
            segments = [s for s in urlparse(clean_href).path.split("/") if s]
            produits_links.add((len(segments), clean_href))
        log.info(f"  {len(produits_links)} liens /fr/produits/* trouvés depuis la home, par profondeur :")
        for n, h in sorted(produits_links):
            log.info(f"    [{n}] {h}")

        browser.close()


if __name__ == "__main__":
    main()
