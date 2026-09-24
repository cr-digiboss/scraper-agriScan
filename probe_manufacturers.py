"""
Script de sondage temporaire — à supprimer après usage.
Güttler, round 2 : guettler.com est le site d'un musicien (Ludwig
Güttler), pas le fabricant agricole (rouleaux/packers, gamme connue
"Green Master"). Recherche du vrai domaine.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


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

        for label, url in [
            ("guettler-agrar.de", "https://www.guettler-agrar.de/"),
            ("guettler-bodenbearbeitung.de", "https://www.guettler-bodenbearbeitung.de/"),
            ("hguettler.de", "https://www.hguettler.de/"),
            ("greenmaster-guettler.com", "https://www.greenmaster-guettler.com/"),
            ("guettler-agri.fr", "https://www.guettler-agri.fr/"),
            ("guettler.fr", "https://www.guettler.fr/"),
            ("guettler-gmbh.de", "https://www.guettler-gmbh.de/"),
        ]:
            try_url(page, label, url)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
