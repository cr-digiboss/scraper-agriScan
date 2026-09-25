"""
Script de sondage temporaire — à supprimer après usage.
New Holland : voir la liste complète des liens produits/tracteurs.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        base_path = scraper.NEW_HOLLAND_CATEGORIES[0]
        page.goto(base_path, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(6000)

        all_hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        log.info(f"Nombre total de liens <a> : {len(all_hrefs)}")
        nh_hrefs = sorted(set(h for h in all_hrefs if "newholland.com" in h))
        log.info(f"Liens newholland.com uniques : {len(nh_hrefs)}")
        for h in nh_hrefs:
            log.info(f"  {h}")

        # essaie aussi de scroller pour déclencher un éventuel lazy-load
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        all_hrefs2 = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        nh_hrefs2 = sorted(set(h for h in all_hrefs2 if "newholland.com" in h))
        log.info(f"\nAprès scroll : {len(nh_hrefs2)} liens newholland.com uniques")
        nouveaux = set(nh_hrefs2) - set(nh_hrefs)
        for h in sorted(nouveaux):
            log.info(f"  NOUVEAU : {h}")

        browser.close()


if __name__ == "__main__":
    main()
