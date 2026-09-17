"""
Script de sondage temporaire — à supprimer après usage.
Cherche comment découvrir les fiches produit Pöttinger (pattern
/produkte/detail/<slug>/<nom>) depuis une page catégorie, pour valider
la stratégie de crawl avant d'écrire le scraper définitif. Ne touche pas
à la base de données.
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

POETTINGER_URLS = [
    "https://www.poettinger.at/fr_be/produkte",
    "https://www.poettinger.at/fr_be/",
]


def probe_links(page, url):
    log.info(f"\n{'=' * 80}\n{url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(4000)
        for _ in range(6):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(400)

        hrefs = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        product_links = []
        category_links = []
        for h in hrefs:
            u = urlparse(h["href"])
            if "poettinger.at" not in u.netloc:
                continue
            if "/produkte/detail/" in u.path:
                product_links.append(h)
            elif "/produkte/" in u.path and u.path.rstrip("/") != "/fr_be/produkte":
                category_links.append(h)

        seen = set()
        uniq_products = []
        for l in product_links:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq_products.append(l)

        seen2 = set()
        uniq_categories = []
        for l in category_links:
            if l["href"] not in seen2:
                seen2.add(l["href"])
                uniq_categories.append(l)

        log.info(f"Liens fiches produit (/produkte/detail/) : {len(uniq_products)}")
        for l in uniq_products[:20]:
            log.info(f"  [{l['text'][:50]:50}] {l['href']}")

        log.info(f"Liens catégorie (/produkte/...) : {len(uniq_categories)}")
        for l in uniq_categories[:20]:
            log.info(f"  [{l['text'][:50]:50}] {l['href']}")

    except Exception as e:
        log.error(f"Erreur sur {url} : {e}")


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
        for url in POETTINGER_URLS:
            probe_links(page, url)
        browser.close()


if __name__ == "__main__":
    main()
