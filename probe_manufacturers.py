"""
Script de sondage temporaire — à supprimer après usage.
Case IH round modeles-3 : le sélecteur ".series-details__tab-button" ne
matche rien. On dump tous les éléments dont la classe contient "tab"
(nom + classe complète) pour trouver le vrai sélecteur des onglets
Aperçu/Caractéristiques/Brochures.
"""

import logging

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

        info = page.evaluate(
            """
            () => {
                const els = Array.from(document.querySelectorAll('[class*="tab"]'));
                return els.map(e => ({
                    tag: e.tagName,
                    cls: e.className,
                    text: e.innerText ? e.innerText.trim().slice(0, 40) : '',
                }));
            }
            """
        )
        log.info(f"{len(info)} éléments avec 'tab' dans la classe :")
        for e in info:
            log.info(f"  <{e['tag']} class=\"{e['cls']}\"> texte: {e['text']!r}")

        browser.close()


if __name__ == "__main__":
    main()
