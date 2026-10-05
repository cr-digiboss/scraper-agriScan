"""
Script de sondage temporaire — à supprimer après usage.
Case IH round modeles-4 : le vrai sélecteur d'onglet est
".navigation-bar__tab" (Aperçu/Caractéristiques/Brochures). On clique sur
"Caractéristiques" et "Brochures" avec ce bon sélecteur.
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

        try:
            accept = page.locator("#onetrust-accept-btn-handler")
            if accept.is_visible(timeout=3000):
                accept.click(timeout=3000)
                log.info("bannière cookies fermée")
                page.wait_for_timeout(1000)
        except Exception as e:
            log.info(f"pas de bannière cookies (ou échec fermeture) : {e}")

        def click_visible_tab(text):
            """Deux copies du bandeau d'onglets existent dans le DOM (desktop
            + mobile, l'une cachée en CSS) : on clique celle qui est visible."""
            locs = page.locator(".navigation-bar__tab", has_text=text)
            n = locs.count()
            for i in range(n):
                loc = locs.nth(i)
                if loc.is_visible():
                    loc.click(timeout=5000)
                    return True
            return False

        log.info("=== Clic sur Caractéristiques ===")
        ok = click_visible_tab("Caractéristiques")
        log.info(f"clic réussi : {ok}")
        page.wait_for_timeout(3000)

        n_tables = len(page.query_selector_all("table"))
        log.info(f"{n_tables} tables")
        if n_tables:
            rows = page.query_selector_all("table")[0].query_selector_all("tr")
            log.info(f"table0: {len(rows)} rows")
            for r in rows[:5]:
                cells = r.query_selector_all("td, th")
                log.info(f"  row: {[c.inner_text().strip()[:30] for c in cells]}")

        # Cherche un sélecteur de modèle (dropdown/select) dans la section
        # Caractéristiques.
        selects = page.query_selector_all("select")
        log.info(f"\n{len(selects)} <select> trouvés")
        for s in selects:
            opts = s.query_selector_all("option")
            log.info(f"  options: {[o.inner_text().strip() for o in opts]}")

        body_text = page.inner_text("body")
        idx = body_text.find("Moteur")
        log.info(f"\ntexte autour de 'Moteur' (2000 car.) :\n{body_text[idx:idx+2000] if idx!=-1 else '(non trouvé)'}")

        log.info("\n=== Clic sur Brochures ===")
        ok = click_visible_tab("Brochures")
        log.info(f"clic réussi : {ok}")
        page.wait_for_timeout(3000)
        hrefs = page.eval_on_selector_all("a[href$='.pdf']", "els => els.map(e => e.href)")
        log.info(f"{len(hrefs)} liens PDF :")
        for h in hrefs:
            log.info(f"  {h}")
        body_text2 = page.inner_text("body")
        log.info(f"\ntexte body après clic Brochures (2000 premiers car.) :\n{body_text2[:2000]}")

        browser.close()


if __name__ == "__main__":
    main()
