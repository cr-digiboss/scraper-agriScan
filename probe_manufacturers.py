"""
Script de sondage temporaire — à supprimer après usage.
Lot 1 round 6 :
- Horsch : la fiche produit a des paires label/valeur en texte mais pas de
  <table> -> chercher la vraie structure DOM (dl/dt/dd, ou classes CSS)
- Amazone : round précédent a inspecté la page catégorie par erreur (le
  premier lien "pertinent" était la catégorie elle-même) -> viser une vraie
  fiche produit (ZA-X Perfect)
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def accept_cookies(page):
    for text in ["Tout accepter", "Accepter tout", "Accept all", "J'accepte", "Accepter"]:
        try:
            btn = page.get_by_text(text, exact=False).first
            if btn.is_visible(timeout=1500):
                btn.click(timeout=1500)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Horsch : chercher la structure DOM des paires label/valeur
        page = browser.new_page(user_agent=UA)
        page.goto(
            "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques/joker-4-6-hd",
            timeout=25000, wait_until="domcontentloaded",
        )
        page.wait_for_timeout(2500)
        log.info("\n=== Horsch Joker 4-6 HD : structure DOM ===")
        for sel in ["dl", "dt", "dd", "[class*='techdata']", "[class*='tech-data']",
                    "[class*='spec']", "[class*='fact']", "[class*='value']", "[class*='key']"]:
            els = page.query_selector_all(sel)
            log.info(f"  {sel} -> {len(els)} élément(s)")
            for e in els[:6]:
                t = e.inner_text().strip().replace("\n", " | ")[:100]
                if t:
                    log.info(f"    {t}")
        # Chercher un conteneur parent commun en remontant depuis le texte "Largeur de travail"
        try:
            loc = page.get_by_text("Largeur de travail", exact=False).first
            html = loc.evaluate("el => el.closest('div') ? el.closest('div').outerHTML.slice(0, 800) : 'no div parent'")
            log.info(f"  Parent HTML autour de 'Largeur de travail' :\n{html}")
        except Exception as e:
            log.warning(f"  Recherche parent échouée: {e}")
        page.close()

        # Amazone : vraie fiche produit ZA-X Perfect
        page = browser.new_page(user_agent=UA)
        url = "https://amazone.fr/fr-fr/produits-et-solutions-digitales/machines-agricoles/fertilisation/epandeurs-portes/epandeur-centrifuge-amazone-za-x-perfect-294334"
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1500)
        log.info(f"\n=== Amazone ZA-X Perfect : title={page.title()!r}")
        tables = page.query_selector_all("table")
        log.info(f"  {len(tables)} table(s)")
        for i, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"  table {i}: {len(rows)} lignes")
            for r in rows[:6]:
                cells = r.query_selector_all("td, th")
                log.info(f"    row: {[c.inner_text().strip()[:40] for c in cells]}")
        text = page.inner_text("body")
        log.info(f"  body text (1500 car.) : {text[:1500]!r}")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
