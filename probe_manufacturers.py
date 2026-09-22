"""
Script de sondage temporaire — à supprimer après usage.
Lot 8, round 1 : découverte de structure pour 4 marques
(Sulky, Rauch, Lely, Same/Landini).
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

TARGETS = {
    "Sulky": "https://www.sulky-burel.com/fr/nos-produits",
    "Rauch": "https://www.rauch.de/fr/produits",
    "Lely": "https://www.lely.com/fr/",
    "Same": "https://www.same-tractors.com/fr/produits",
}


def dump_links(page, netloc_hint):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    seen = set()
    samples = []
    for href in hrefs:
        u = urlparse(href)
        if netloc_hint not in u.netloc:
            continue
        if href in seen:
            continue
        seen.add(href)
        samples.append(href)
    log.info(f"  Total liens bruts : {len(hrefs)}")
    log.info(f"  Liens internes uniques ({netloc_hint}) : {len(samples)}")
    for s in samples[:30]:
        log.info(f"    {s}")


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

        for brand, url in TARGETS.items():
            log.info(f"\n===== {brand} : {url} =====")
            page = context.new_page()
            try:
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(3500)
                for _ in range(5):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(300)
                title = page.title()
                log.info(f"  Titre : {title}")
                netloc_hint = urlparse(url).netloc.replace("www.", "")
                dump_links(page, netloc_hint)
            except Exception as e:
                log.info(f"  ERREUR : {e!r}")
            finally:
                page.close()

        browser.close()


if __name__ == "__main__":
    main()
