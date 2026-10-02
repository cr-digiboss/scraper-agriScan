"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland round 3 : inspecter une fiche produit individuelle
(ex. T7 Standard) pour voir si un bouton "voir plus de modèles" y révèle
des variantes/modèles non capturés par le tableau de specs actuel.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def inspect(page, url, label):
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        log.info(f"\n--- {label} : {url} title={page.title()!r}")
        tables = page.query_selector_all("table")
        log.info(f"    {len(tables)} table(s)")

        candidates = page.eval_on_selector_all(
            "button, a, div[role='button'], span[role='button']",
            "els => els.filter(e => /mod[eè]le|voir plus|afficher plus|view more|show more/i.test(e.textContent)).map(e => e.tagName + ':' + e.textContent.trim().slice(0,60))"
        )
        log.info(f"    éléments mentionnant 'modèle'/'voir plus' : {candidates[:20]}")

        text = page.inner_text("body")
        log.info(f"    body text ({len(text)} car. ; 2500 affichés) : {text[:2500]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        inspect(page, "https://agriculture.newholland.com/fr-be/europe/produits/tracteurs", "Tracteurs (recherche lien T7 STANDARD)")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        t7_links = [h for h in hrefs if "t7" in h.lower() and "newholland.com" in h]
        log.info(f"\nLiens T7 trouvés : {t7_links[:10]}")
        page.close()

        if t7_links:
            page = browser.new_page(user_agent=UA)
            inspect(page, t7_links[0], "Fiche T7")
            page.close()

        browser.close()


if __name__ == "__main__":
    main()
