"""
Script de sondage temporaire — à supprimer après usage.
Vérifie si des fiches produit précises contiennent des tableaux de specs exploitables.
Ne touche pas à la base de données.
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

SITES = {
    "Kverneland (fiche modèle 2300 S Variomat)": "https://ien.kverneland.com/ploughs/reversible-ploughs/kverneland-2300-s-variomat",
    "Horsch (fiche modèle Pronto 6-7 DC)": "https://www.horsch.com/produkte/saemaschinen/scheibensaemaschinen/pronto-6-7-dc",
    "Claas (fiche gamme Arion 400)": "https://www.claas.com/fr-fr/machines-agricoles/tracteurs/arion-400",
}


def probe(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(5):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(800)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> sur la page : {len(tables)}")
        for i, t in enumerate(tables[:5]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            if rows:
                first_row_text = rows[0].inner_text().replace("\n", " | ")
                log.info(f"    1ère ligne : {first_row_text[:150]}")

        # Chercher aussi des blocs "dl/dt/dd" ou des divs avec spec/technical dans la classe
        dls = page.query_selector_all("dl")
        log.info(f"Nombre de <dl> sur la page : {len(dls)}")

        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i]"
        )
        log.info(f"Nombre d'éléments avec classe contenant spec/technical/caracteristique : {len(spec_divs)}")
        for d in spec_divs[:3]:
            txt = d.inner_text().strip().replace("\n", " | ")
            if txt:
                log.info(f"    échantillon : {txt[:200]}")

        # Chercher des liens PDF (brochure/fiche technique)
        pdf_links = page.eval_on_selector_all(
            "a[href*='.pdf' i]",
            "els => els.map(e => e.href)"
        )
        log.info(f"Liens PDF trouvés : {len(pdf_links)}")
        for p in pdf_links[:5]:
            log.info(f"    {p}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


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
        for name, url in SITES.items():
            probe(name, url, page)
        browser.close()


if __name__ == "__main__":
    main()
