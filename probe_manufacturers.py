"""
Script de sondage temporaire — à supprimer après usage.
Round 3 : round 2 tronquait l'en-tête affiché à 25 caractères pour l'affichage,
ce qui a pu masquer du texte distinctif après ce point (le scraper réel, lui,
n'utilise pas de troncature). On réaffiche le texte complet des en-têtes de la
page "EUROCAT Alpha Motion", + on inspecte le HTML brut des cellules d'en-tête
(colspan éventuel) pour confirmer si colonnes 1/2 sont vraiment identiques.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://www.poettinger.at/fr_be/produkte/detail/euam/eurocat-alpha-motion-faucheuses-a-tambours-frontales"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(6):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(250)

        tables = page.query_selector_all("table")
        log.info(f"{len(tables)} tables sur la page")
        for i, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            if not rows:
                continue
            cells0 = rows[0].query_selector_all("td, th")
            log.info(f"\n--- table {i} : en-tête complet (sans troncature) ---")
            for j, c in enumerate(cells0):
                full_text = c.inner_text().strip()
                colspan = c.get_attribute("colspan")
                outer_html = c.evaluate("el => el.outerHTML")[:300]
                log.info(f"  col {j}: colspan={colspan!r} texte={full_text!r}")
                log.info(f"         html={outer_html!r}")

            # Quelques lignes de données pour voir si les valeurs diffèrent entre
            # colonnes 1 et 2 (si oui, ce sont bien 2 modèles distincts malgré le
            # nom identique — peut-être une variante largeur/couleur).
            log.info(f"  -- 5 premières lignes de données --")
            for row in rows[1:6]:
                cells = row.query_selector_all("td, th")
                vals = [c.inner_text().strip()[:40] for c in cells]
                log.info(f"    {vals}")

        browser.close()


if __name__ == "__main__":
    main()
