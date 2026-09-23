"""
Script de sondage temporaire — à supprimer après usage.
Round 3 :
- Deutz-Fahr : inspecter le contenu réel des 17 éléments class*=spec sur
  la page série (per-modèle exploitable ou marketing générique par
  gamme, comme Case IH ?).
- Mahindra : mahindra.eu est un domaine à vendre (parking page), les
  autres essais échouent en DNS. Nouvelles tentatives ciblées France/
  Europe avant abandon éventuel.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect_deutzfahr_specs(page, url):
    log.info(f"\n===== Deutz-Fahr specs : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        specish = page.query_selector_all("[class*='spec' i]")
        log.info(f"  Éléments class*=spec : {len(specish)}")
        for i, el in enumerate(specish):
            txt = el.inner_text().strip().replace("\n", " | ")
            if txt:
                log.info(f"  [{i}] {txt[:400]}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def try_url(page, label, url):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        log.info(f"  OK — Titre : {page.title()} — URL finale : {page.url}")
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

        inspect_deutzfahr_specs(page, "https://www.deutz-fahr.com/fr-fr/tracteurs/serie-9-stage-5")

        log.info("\n===== Recherche Mahindra France/Europe (suite) =====")
        for label, url in [
            ("mahindra.fr", "https://www.mahindra.fr/"),
            ("mahindra-tracteurs.fr", "https://www.mahindra-tracteurs.fr/"),
            ("mahindra-tractors.eu", "https://www.mahindra-tractors.eu/"),
            ("mahindra.com global", "https://www.mahindra.com/"),
            ("mahindra farm division", "https://www.mahindrafarmdivision.com/"),
        ]:
            try_url(page, label, url)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
