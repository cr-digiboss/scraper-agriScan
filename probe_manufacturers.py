"""
Script de sondage temporaire — à supprimer après usage.
Vérifie les tableaux de specs sur une vraie fiche modèle pour Amazone,
John Deere et Kuhn. Ne touche pas à la base de données.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

PAGES = {
    "Amazone (charrue Teres 300)": "https://amazone.net/fr/produits-et-solutions-digitales/machines-agricoles/travail-du-sol/charrues/charrue-port%C3%A9e-teres-300-1084002",
    "John Deere (6M 230)": "https://www.deere.be/fr/tracteurs/moyenne/s%C3%A9rie-6m/6m230/",
    "Kuhn (Euromix 3 DL)": "https://www.kuhn.com/fr/elevage/melangeuses-trainees/melangeuses-3-vis-verticales/euromix-3-dl",
}


def probe(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(6):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(600)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> sur la page : {len(tables)}")
        for i, t in enumerate(tables[:5]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            for r in rows[:2]:
                txt = r.inner_text().replace("\n", " | ")
                log.info(f"    ligne : {txt[:180]}")

        dls = page.query_selector_all("dl")
        log.info(f"Nombre de <dl> sur la page : {len(dls)}")
        if dls:
            log.info(f"    échantillon dl[0] : {dls[0].inner_text()[:250].replace(chr(10), ' | ')}")

        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], "
            "[class*='fiche-technique' i], [class*='donnees-techniques' i]"
        )
        log.info(f"Éléments avec classe spec/technical/caractéristique : {len(spec_divs)}")
        for d in spec_divs[:3]:
            txt = d.inner_text().strip().replace("\n", " | ")
            if txt:
                log.info(f"    échantillon : {txt[:250]}")

        pdf_links = page.eval_on_selector_all("a[href*='.pdf' i]", "els => els.map(e => e.href)")
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
        for name, url in PAGES.items():
            probe(name, url, page)
        browser.close()


if __name__ == "__main__":
    main()
