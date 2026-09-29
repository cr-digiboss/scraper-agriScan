"""
Script de sondage temporaire — à supprimer après usage.
Le fix wait_for_selector(state="attached") échoue quasi instantanément
(pas un vrai timeout de 6s) -> logger l'exception réelle pour comprendre.
"""

import logging
import time

from playwright.sync_api import sync_playwright

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

        t0 = time.time()
        try:
            container = page.wait_for_selector("[class*='fact']", timeout=6000, state="attached")
            log.info(f"OK en {time.time()-t0:.2f}s : {container}")
        except Exception as e:
            log.error(f"ECHEC en {time.time()-t0:.2f}s : {type(e).__name__}: {e}")

        # Vérifier avec query_selector simple (sans wait) juste après domcontentloaded
        c2 = page.query_selector("[class*='fact']")
        log.info(f"query_selector direct (sans wait) juste après domcontentloaded : {c2}")

        page.wait_for_timeout(3000)
        c3 = page.query_selector("[class*='fact']")
        log.info(f"query_selector direct après 3s d'attente : {c3}")
        if c3:
            log.info(f"  inner_text (300 car.) : {c3.inner_text()[:300]!r}")

        browser.close()


if __name__ == "__main__":
    main()
