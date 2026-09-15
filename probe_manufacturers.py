"""
Script de sondage temporaire — à supprimer après usage.
Explore la structure de quelques sites constructeurs pour préparer un futur scraper.
Ne touche pas à la base de données.
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

SITES = {
    "Claas (tracteurs, URL corrigée)": "https://www.claas.com/fr-fr/machines-agricoles/tracteurs",
    "Kverneland (page d'accueil)": "https://www.kverneland.com/",
    "Horsch (catégorie semoirs)": "https://www.horsch.com/produkte/saemaschinen",
}


def probe(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(2000)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> sur la page : {len(tables)}")

        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        final_domain = urlparse(page.url).netloc
        root_domain = ".".join(final_domain.split(".")[-2:])  # ex: claas.com
        internal = [l for l in links if root_domain in l["href"] and l["text"]]
        seen = set()
        uniq = []
        for l in internal:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)

        log.info(f"Domaine racine utilisé pour filtrer : {root_domain}")
        log.info(f"Liens internes uniques trouvés : {len(uniq)} (échantillon des 50 premiers)")
        for l in uniq[:50]:
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
            viewport={"width": 1280, "height": 1600},
        )
        page = context.new_page()
        for name, url in SITES.items():
            probe(name, url, page)
        browser.close()


if __name__ == "__main__":
    main()
