"""
Script de sondage temporaire — à supprimer après usage.
Güttler, round 3 : vrai domaine trouvé via recherche web = guettler.org
(pas .com, qui appartient à un musicien homonyme). Exploration + recherche
d'une version française.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def explore(page, label, url):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        log.info(f"  Titre : {title} — URL finale : {page.url}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = []
        for href in hrefs:
            h = href.split("?")[0].split("#")[0]
            if h not in seen:
                seen.append(h)
        log.info(f"  Liens uniques : {len(seen)}")
        for s in seen[:60]:
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

        explore(page, "Güttler (guttler.org)", "https://sub.guttler.org/de")
        explore(page, "Güttler racine", "https://guttler.org/")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
