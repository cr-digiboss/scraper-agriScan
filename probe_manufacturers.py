"""
Script de sondage temporaire — à supprimer après usage.
Le conteneur "[class*='fact']" est trouvé instantanément et son inner_text
contient bien les données -> le bug est dans la boucle sur les divs enfants
(small+strong). Logger le détail div par div.
"""

import logging

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

        container = page.wait_for_selector("[class*='fact']", timeout=6000, state="attached")
        log.info(f"container trouvé : {container}")

        divs = container.query_selector_all("div")
        log.info(f"{len(divs)} div(s) enfant(s) trouvé(s)")
        for i, div in enumerate(divs):
            smalls = div.query_selector_all("small")
            strong = div.query_selector("strong")
            cls = div.get_attribute("class")
            log.info(f"  div[{i}] class={cls!r} smalls={len(smalls)} strong={'oui' if strong else 'non'}")
            if smalls and strong:
                log.info(f"    -> label={smalls[0].inner_text()!r} value={strong.inner_text()!r}")

        browser.close()


if __name__ == "__main__":
    main()
