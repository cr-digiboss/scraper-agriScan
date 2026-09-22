"""
Script de sondage temporaire — à supprimer après usage.
John Deere, round 1 : découverte de structure sur deere.com (catalogue
actuel, pas TractorData qui est désactivé car trop volumineux/historique).
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URL = "https://www.deere.fr/fr/agriculture/"


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
        log.info(f"\n===== John Deere : {URL} =====")
        try:
            page.goto(URL, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            for _ in range(6):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(300)
            title = page.title()
            log.info(f"  Titre : {title}")
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            seen = set()
            samples = []
            for href in hrefs:
                u = urlparse(href)
                if "deere" not in u.netloc:
                    continue
                if href in seen:
                    continue
                seen.add(href)
                samples.append(href)
            log.info(f"  Total liens bruts : {len(hrefs)}")
            log.info(f"  Liens internes uniques (deere) : {len(samples)}")
            for s in samples[:40]:
                log.info(f"    {s}")
        except Exception as e:
            log.info(f"  ERREUR : {e!r}")
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
