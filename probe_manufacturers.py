"""
Script de sondage temporaire — à supprimer après usage.
Lot 3, round 4 : vérifie les specs sur une fiche modèle Kubota France
(m4003) désormais accessible via ke.kubota-eu.com. Ne touche pas à la base
de données.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

KUBOTA_MODEL_URL = "https://ke.kubota-eu.com/agriculture/fr/products/m4003/"


def probe_kubota_model(page):
    log.info(f"\n{'=' * 80}\nKubota M4003 — {KUBOTA_MODEL_URL}\n{'=' * 80}")
    try:
        resp = page.goto(KUBOTA_MODEL_URL, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(6):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(600)
        log.info(f"Titre : {page.title()}")

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")
        for i, t in enumerate(tables[:6]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            for r in rows[:3]:
                log.info(f"    ligne : {r.inner_text().replace(chr(10), ' | ')[:180]}")

        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i]"
        )
        log.info(f"Éléments classe spec/technical : {len(spec_divs)}")
        for i, d in enumerate(spec_divs[:6]):
            cls = d.get_attribute("class")
            txt = d.inner_text().strip().replace("\n", " | ")
            log.info(f"  [{i}] class={cls}")
            log.info(f"      texte ({len(txt)} car.) : {txt[:400]}")

        pdf_links = page.eval_on_selector_all("a[href*='.pdf' i]", "els => els.map(e => e.href)")
        log.info(f"PDF trouvés : {len(pdf_links)}")
        for p in pdf_links[:3]:
            log.info(f"    {p}")

    except Exception as e:
        log.error(f"Erreur Kubota M4003 : {e}")


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
        probe_kubota_model(page)
        browser.close()


if __name__ == "__main__":
    main()
