"""
Script de sondage temporaire — à supprimer après usage.
Kubota, round 6 :
- La fiche produit m4003 n'a aucune <table> et un seul élément
  class*=spec (contenu à inspecter). Vérifier si les caractéristiques
  sont dans un onglet/accordéon chargé par JS, un PDF, ou ailleurs.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect_kubota_full(page, url):
    log.info(f"\n===== Kubota produit (détaillé) : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(12):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)

        # contenu du seul élément class*=spec trouvé au round précédent
        specish = page.query_selector_all("[class*='spec' i]")
        log.info(f"  Éléments class*=spec : {len(specish)}")
        for el in specish:
            log.info("  --- contenu ---")
            log.info("  " + el.inner_text()[:1500].replace("\n", " | "))

        # chercher des onglets / accordéons
        tabs = page.query_selector_all("[role='tab'], .tab, .tabs, [class*='tab' i], [class*='accordion' i]")
        log.info(f"  Éléments tab/accordion-like : {len(tabs)}")
        for el in tabs[:10]:
            txt = el.inner_text().strip().replace("\n", " ")[:80]
            log.info(f"    {txt}")

        # chercher des liens PDF
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        pdfs = [h for h in hrefs if ".pdf" in h.lower()]
        log.info(f"  Liens PDF : {len(pdfs)}")
        for p in pdfs[:10]:
            log.info(f"    {p}")

        # chercher un mot-clé "caractéristiques" / "spécifications" dans le texte de la page
        body_text = page.inner_text("body")
        for kw in ["Caractéristiques", "Spécifications", "Fiche technique"]:
            idx = body_text.find(kw)
            log.info(f"  Occurrence '{kw}' à l'index {idx}")
            if idx >= 0:
                log.info("    Contexte : " + body_text[idx:idx+300].replace("\n", " | "))

        # nombre total d'éléments <div> pour se faire une idée de la densité JS
        log.info(f"  Longueur totale du texte body : {len(body_text)}")
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

        inspect_kubota_full(page, "https://ke.kubota-eu.com/agriculture/fr/products/m4003/")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
