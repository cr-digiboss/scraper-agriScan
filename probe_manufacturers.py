"""
Script de sondage temporaire — à supprimer après usage.
Case IH round modeles-8 : le clic sur CONFIGURER échoue (barre de nav
sticky qui intercepte le pointeur). On visite directement l'URL du
configurateur déjà repérée (/outils-et-ressources/configurateur) pour
voir sa structure (sélection de gamme/modèle, specs par modèle ?).
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

URL = "https://www.caseih.com/fr-fr/france/outils-et-ressources/configurateur"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        try:
            accept = page.locator("#onetrust-accept-btn-handler")
            if accept.is_visible(timeout=3000):
                accept.click(timeout=3000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        log.info(f"URL finale : {page.url}")
        log.info(f"titre : {page.title()}")

        n_tables = len(page.query_selector_all("table"))
        log.info(f"{n_tables} tables")

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        base_netloc = urlparse(page.url).netloc
        same_domain = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if urlparse(h).netloc == base_netloc))
        log.info(f"\n{len(same_domain)} liens même domaine :")
        for h in same_domain:
            log.info(f"  {h}")

        body_text = page.inner_text("body")
        log.info(f"\ntexte body (3000 premiers car.) :\n{body_text[:3000]}")

        browser.close()


if __name__ == "__main__":
    main()
