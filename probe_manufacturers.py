"""
Script de sondage temporaire — à supprimer après usage.
Lot 1 round 7 :
- Amazone : cliquer sur l'onglet "CARACTÉRISTIQUES" (comme sur Vicon) pour
  voir si un tableau de specs apparaît après interaction
- Maschio Gaspardo : tester avec des délais beaucoup plus longs entre les
  requêtes pour voir si l'anti-bot (Client Challenge) se déclenche moins
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

        # --- Amazone : cliquer sur CARACTÉRISTIQUES ---
        page = browser.new_page(user_agent=UA)
        url = "https://amazone.fr/fr-fr/produits-et-solutions-digitales/machines-agricoles/fertilisation/epandeurs-portes/epandeur-centrifuge-amazone-za-x-perfect-294334"
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1000)

        log.info("\n=== Amazone : recherche d'onglets/liens 'CARACTERISTIQUES' ===")
        for text in ["CARACTÉRISTIQUES", "Caractéristiques", "Caractéristiques techniques", "Données techniques"]:
            try:
                loc = page.get_by_text(text, exact=False)
                count = loc.count()
                log.info(f"  '{text}' -> {count} occurrence(s)")
                if count:
                    loc.first.click(timeout=3000)
                    page.wait_for_timeout(2500)
                    tables = page.query_selector_all("table")
                    log.info(f"    après clic : {len(tables)} table(s)")
                    for t in tables[:2]:
                        rows = t.query_selector_all("tr")
                        for r in rows[:5]:
                            cells = r.query_selector_all("td, th")
                            log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
                    body = page.inner_text("body")
                    idx = body.lower().find("caractéristique")
                    if idx >= 0:
                        log.info(f"    contexte texte autour de 'caractéristique': {body[idx:idx+600]!r}")
            except Exception as e:
                log.warning(f"  '{text}' -> échec ({e})")

        # Chercher aussi des iframes (widget externe de specs)
        frames = page.frames
        log.info(f"  {len(frames)} frame(s) sur la page: {[f.url for f in frames]}")
        page.close()

        # --- Maschio Gaspardo : délais longs, contexte frais ---
        log.info("\n=== Maschio Gaspardo : retry avec délais longs ===")
        urls = [
            "https://www.maschiogaspardo.com/fr_fr/",
            "https://www.maschiogaspardo.com/fr_fr/bora.html",
            "https://www.maschiogaspardo.com/fr_fr/all-products",
        ]
        for url in urls:
            context = browser.new_context(user_agent=UA, locale="fr-FR")
            page = context.new_page()
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(8000)
                title = page.title()
                log.info(f"  {url} -> title={title!r}")
                if "challenge" not in title.lower() and title:
                    tables = page.query_selector_all("table")
                    spec_divs = page.query_selector_all("[class*='spec' i], [class*='caract' i], [class*='attribute' i]")
                    log.info(f"    {len(tables)} table(s), {len(spec_divs)} div(s) spec/caract/attribute")
                    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                    htmls = [h for h in hrefs if h.endswith(".html") and "maschiogaspardo.com" in h]
                    log.info(f"    {len(set(htmls))} liens .html")
            except Exception as e:
                log.warning(f"  {url} -> échec ({e})")
            context.close()
            page = browser.new_page(user_agent=UA)  # pause implicite via nouvel objet
            page.wait_for_timeout(6000)
            page.close()

        browser.close()


if __name__ == "__main__":
    main()
