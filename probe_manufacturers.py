"""
Script de sondage temporaire — à supprimer après usage.
Vérifie si des fiches produit précises (lot 1) contiennent des tableaux de
specs exploitables. Ne touche pas à la base de données.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

PAGES = {
    "Amazone (sous-catégorie charrues)": "https://amazone.net/fr/produits-et-solutions-digitales/machines-agricoles/travail-du-sol/charrues",
    "Case IH (Farmall M)": "https://www.caseih.com/fr-be/belux/produits/tracteurs/gamme-farmall/farmall-m",
    "Fendt (900 Vario)": "https://www.fendt.com/fr/machines-agricoles/tracteurs/fendt-900-vario",
    "John Deere (Série 6M)": "https://www.deere.be/fr/tracteurs/moyenne/s%C3%A9rie-6m/",
    "Kuhn (mélangeuses 3 vis)": "https://www.kuhn.com/fr/elevage/melangeuses-trainees/melangeuses-3-vis-verticales",
    "Massey Ferguson (MF 8S)": "https://www.masseyferguson.com/fr_fr/product/tractors/mf-8s.html",
}


def probe(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(5):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(600)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> sur la page : {len(tables)}")
        for i, t in enumerate(tables[:4]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            if rows:
                first = rows[0].inner_text().replace("\n", " | ")
                log.info(f"    1ère ligne : {first[:150]}")
                if len(rows) > 1:
                    second = rows[1].inner_text().replace("\n", " | ")
                    log.info(f"    2e ligne   : {second[:150]}")

        dls = page.query_selector_all("dl")
        log.info(f"Nombre de <dl> sur la page : {len(dls)}")
        if dls:
            log.info(f"    échantillon dl[0] : {dls[0].inner_text()[:200].replace(chr(10), ' | ')}")

        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], "
            "[class*='fiche-technique' i], [class*='donnees-techniques' i]"
        )
        log.info(f"Éléments avec classe spec/technical/caractéristique : {len(spec_divs)}")
        for d in spec_divs[:3]:
            txt = d.inner_text().strip().replace("\n", " | ")
            if txt:
                log.info(f"    échantillon : {txt[:200]}")

        pdf_links = page.eval_on_selector_all("a[href*='.pdf' i]", "els => els.map(e => e.href)")
        log.info(f"Liens PDF trouvés : {len(pdf_links)}")
        for p in pdf_links[:5]:
            log.info(f"    {p}")

        # Sous-liens produits éventuels (utile si la page est encore une catégorie)
        sub_links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.href)"
        )
        log.info(f"Total liens sur la page : {len(sub_links)}")

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
