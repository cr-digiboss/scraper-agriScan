"""
Script de sondage temporaire — à supprimer après usage.
Round 4 : Mahindra abandonné (aucun site France/Europe accessible après
8 tentatives). On ne revalide que Deutz-Fahr (timeout transitoire au
round précédent) pour voir le contenu réel des éléments class*=spec.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect_deutzfahr_specs(page, url):
    log.info(f"\n===== Deutz-Fahr specs : {url} =====")
    try:
        page.goto(url, timeout=35000, wait_until="domcontentloaded")
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

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
