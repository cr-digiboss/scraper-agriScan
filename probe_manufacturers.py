"""
Script de sondage temporaire — à supprimer après usage.
Case IH / Kubota, round 4 :
- Case IH : vérifier une 2e fiche (Farmall, plus petite gamme utilitaire)
  pour voir si toutes les pages sont des bannières marketing à 4 specs
  génériques, ou si certaines ont un vrai tableau détaillé par modèle.
- Kubota : suivre vers ke.kubota-eu.com/agriculture/fr/ (sous-domaine
  français trouvé au round 3).
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect_caseih(page, url):
    log.info(f"\n===== Case IH : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre : {title}")
        log.info(f"  Tables : {len(tables)}")
        specish = page.query_selector_all("[class*='hero-banner__specs' i]")
        log.info(f"  Éléments hero-banner__specs : {len(specish)}")
        for el in specish[:6]:
            txt = el.inner_text()
            log.info("    " + txt.replace("\n", " | "))
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def explore_kubota_fr(page):
    url = "https://ke.kubota-eu.com/agriculture/fr/"
    log.info(f"\n===== Kubota FR : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        log.info(f"  Titre : {title}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = set()
        samples = []
        for href in hrefs:
            u = urlparse(href)
            if "kubota" not in u.netloc:
                continue
            clean = href.split("?")[0].split("#")[0]
            if clean in seen:
                continue
            seen.add(clean)
            samples.append(clean)
        log.info(f"  Liens internes uniques : {len(samples)}")
        for s in samples[:40]:
            log.info(f"    {s}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            viewport={"width": 1280, "height": 1600},
        )
        page = context.new_page()

        inspect_caseih(page, "https://www.caseih.com/fr-fr/france/produits/tracteurs/gamme-farmall")
        explore_kubota_fr(page)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
