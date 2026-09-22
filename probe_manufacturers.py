"""
Script de sondage temporaire — à supprimer après usage.
John Deere, round 2 : la home a un format de locale différent
(fr-fr, pas fr) -> repartir de la vraie home et chercher la nav produits.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URL = "https://www.deere.fr/fr-fr"


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
            page.wait_for_timeout(4000)
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
            # Filtrer les liens qui ressemblent à des catégories produits
            interessants = [s for s in samples if any(m in s.lower() for m in ["produit", "product", "tracteur", "machin", "equipement", "materiel"])]
            log.info(f"  Liens 'produits'-like : {len(interessants)}")
            for s in interessants[:30]:
                log.info(f"    {s}")
            log.info("  --- Tous les liens (échantillon) ---")
            for s in samples[:40]:
                log.info(f"    {s}")
        except Exception as e:
            log.info(f"  ERREUR : {e!r}")
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
