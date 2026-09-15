"""
Script de sondage temporaire — à supprimer après usage.
Explore la structure de quelques sites constructeurs pour préparer un futur scraper.
Ne touche pas à la base de données.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

SITES = {
    "Claas": "https://www.claas.fr/produits/tracteurs",
    "Kverneland": "https://www.kverneland.com/farming/products/",
    "Horsch": "https://www.horsch.com/produkte/",
}


def probe(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(3000)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        # Compter tables et liens
        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> sur la page : {len(tables)}")

        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        # Filtrer les liens internes au domaine, dédupliquer, limiter
        domain = url.split("/")[2]
        internal = [l for l in links if domain in l["href"] and l["text"]]
        seen = set()
        uniq = []
        for l in internal:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)

        log.info(f"Liens internes uniques trouvés : {len(uniq)} (échantillon des 40 premiers)")
        for l in uniq[:40]:
            log.info(f"  [{l['text'][:50]:50}] {l['href']}")

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
        )
        page = context.new_page()
        for name, url in SITES.items():
            probe(name, url, page)
        browser.close()


if __name__ == "__main__":
    main()
