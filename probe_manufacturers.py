"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland : la page des barres de coupe Varifeed (exemple donné par
l'utilisateur) pour trouver le vrai bouton "voir plus de modèles" et voir
si cette page est même atteignable depuis les pages catégorie actuelles.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses/barres-de-coupe-varifeed-pour-moissonneuses-batteuses"
CATEGORY_URL = "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # 1) Cette page est-elle liée depuis la page catégorie ?
        page = browser.new_page(user_agent=UA)
        page.goto(CATEGORY_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        found = [h for h in hrefs if "varifeed" in h.lower() or "barres-de-coupe" in h.lower()]
        log.info(f"Liens 'varifeed'/'barres-de-coupe' trouvés sur la page catégorie : {found}")
        page.close()

        # 2) Inspection de la page elle-même
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        log.info(f"\ntitle={page.title()!r}")

        tables = page.query_selector_all("table")
        log.info(f"tables avant clic : {len(tables)}")
        for i, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            log.info(f"  table {i}: {len(rows)} rows")
            for r in rows[:6]:
                cells = r.query_selector_all("td, th")
                log.info(f"    row: {[c.inner_text().strip()[:30] for c in cells]}")

        candidates = page.eval_on_selector_all(
            "button, a, div[role='button'], span[role='button']",
            "els => els.filter(e => /plus|more|voir|afficher|load|charger/i.test(e.textContent) && e.textContent.trim().length < 50).map(e => e.tagName + ':' + e.textContent.trim())"
        )
        log.info(f"éléments candidats 'voir plus' : {candidates}")

        text = page.inner_text("body")
        log.info(f"\nbody text ({len(text)} car. ; 3000 affichés) : {text[:3000]!r}")

        browser.close()


if __name__ == "__main__":
    main()
