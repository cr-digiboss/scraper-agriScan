"""
Script de sondage temporaire — à supprimer après usage.
Case IH round modeles-7 : on clique sur le bouton "CONFIGURER" (plusieurs
occurrences sur la page) pour voir où il mène et s'il expose les modèles
individuels de la gamme Magnum avec leurs specs.
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

URL = "https://www.caseih.com/fr-fr/france/produits/tracteurs/magnum-serie"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        try:
            accept = page.locator("#onetrust-accept-btn-handler")
            if accept.is_visible(timeout=3000):
                accept.click(timeout=3000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # Les boutons CONFIGURER sont peut-être des <a> directs : on
        # regarde d'abord leurs href avant de cliquer.
        hrefs = page.eval_on_selector_all(
            "a",
            """els => els.filter(e => e.innerText && e.innerText.trim().toUpperCase().includes('CONFIGURER'))
                       .map(e => e.href)"""
        )
        log.info(f"hrefs des boutons/liens CONFIGURER : {hrefs}")

        # Sinon, clic réel et observation de la navigation.
        locs = page.locator("text=CONFIGURER")
        n = locs.count()
        log.info(f"\n{n} éléments texte 'CONFIGURER' trouvés")
        clicked = False
        for i in range(n):
            loc = locs.nth(i)
            if loc.is_visible():
                log.info(f"clic sur l'occurrence {i}...")
                try:
                    with page.expect_navigation(timeout=8000):
                        loc.click(timeout=5000)
                    clicked = True
                    break
                except Exception as e:
                    log.info(f"  pas de navigation détectée ({e}), on vérifie l'URL quand même")
                    clicked = True
                    break

        page.wait_for_timeout(3000)
        log.info(f"\nclic effectué : {clicked}")
        log.info(f"URL actuelle : {page.url}")
        log.info(f"titre : {page.title()}")

        n_tables = len(page.query_selector_all("table"))
        log.info(f"{n_tables} tables")

        hrefs2 = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        base_netloc = urlparse(page.url).netloc
        same_domain = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs2 if urlparse(h).netloc == base_netloc))
        log.info(f"\n{len(same_domain)} liens même domaine :")
        for h in same_domain[:40]:
            log.info(f"  {h}")

        body_text = page.inner_text("body")
        log.info(f"\ntexte body (3000 premiers car.) :\n{body_text[:3000]}")

        browser.close()


if __name__ == "__main__":
    main()
