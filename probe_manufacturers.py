"""
Script de sondage temporaire — à supprimer après usage.
Case IH round modeles-2 : la page gamme a des onglets "Aperçu /
Caractéristiques / Brochures" (classe series-details__tab-button). On
clique sur "Caractéristiques" et "Brochures" pour voir si ça révèle les
modèles individuels (le texte mentionne déjà "Magnum 385 et 405").
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

        for tab_name in ["Caractéristiques", "Brochures"]:
            log.info(f"\n{'='*70}\nClic sur l'onglet : {tab_name}")
            try:
                btn = page.locator(".series-details__tab-button", has_text=tab_name).first
                btn.click(timeout=3000)
                page.wait_for_timeout(3000)
            except Exception as e:
                log.info(f"  ERREUR clic: {e}")
                continue

            n_tables = len(page.query_selector_all("table"))
            log.info(f"  {n_tables} tables")

            hrefs = page.eval_on_selector_all("a[href$='.pdf']", "els => els.map(e => e.href)")
            log.info(f"  {len(hrefs)} liens PDF :")
            for h in hrefs:
                log.info(f"    {h}")

            # Panneau actif (zone qui change selon l'onglet)
            active_panel = page.query_selector(".series-details__tab-panel--active, [class*='tab-panel'][class*='active']")
            if active_panel:
                text = active_panel.inner_text()[:2000]
                log.info(f"  texte du panneau actif (2000 car.) :\n{text}")
            else:
                body_text = page.inner_text("body")
                log.info(f"  (pas de panneau identifié) texte body (2000 car. après 'Caractéristiques'):")
                idx = body_text.find(tab_name)
                log.info(body_text[idx:idx+2000] if idx != -1 else body_text[:2000])

        browser.close()


if __name__ == "__main__":
    main()
