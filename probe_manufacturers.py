"""
Script de sondage temporaire — à supprimer après usage.
Lot 3 round 4 :
- Hardi : dump complet du tableau (structure exacte, y compris ligne d'en-tête)
- Tecnoma / Agrifac : chercher un tableau n'importe où sur la page, sans
  dépendre d'un texte de clic précis
- Lely : fixer le clic sur "Caractéristiques" (échoué au round précédent)
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

        # Hardi : dump complet
        page = browser.new_page(user_agent=UA)
        page.goto("https://hardi.com/fr/sprayers/mounted/master", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        try:
            page.get_by_text("Spécifications techniques", exact=False).first.click(timeout=3000)
            page.wait_for_timeout(2000)
        except Exception as e:
            log.warning(f"clic échoué: {e}")
        tables = page.query_selector_all("table")
        log.info(f"=== Hardi Master : {len(tables)} table(s) ===")
        for t in tables:
            rows = t.query_selector_all("tr")
            log.info(f"  table: {len(rows)} lignes")
            for r in rows:
                cells = r.query_selector_all("td, th")
                log.info(f"    row: {[c.inner_text().strip()[:30] for c in cells]}")
        page.close()

        # Tecnoma : chercher un tableau n'importe où, scroller toute la page
        page = browser.new_page(user_agent=UA)
        page.goto("https://www.tecnoma.com/produits/pulverisateur-agricoles/pulverisateur-porte/premis/", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        for _ in range(10):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(300)
        tables = page.query_selector_all("table")
        log.info(f"\n=== Tecnoma Premis (après scroll) : {len(tables)} table(s) ===")
        full_text = page.inner_text("body")
        log.info(f"  texte complet (2000 der. car.) : {full_text[-2000:]!r}")
        page.close()

        # Agrifac : idem
        page = browser.new_page(user_agent=UA)
        page.goto("https://www.agrifac.com/fr/pulverisateurs/vanguard-55/", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        for _ in range(15):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(300)
        tables = page.query_selector_all("table")
        log.info(f"\n=== Agrifac Vanguard 55 (après scroll) : {len(tables)} table(s) ===")
        full_text = page.inner_text("body")
        idx = full_text.lower().find("spécif")
        idx2 = full_text.lower().find("caractéris")
        log.info(f"  'spécif' offset={idx}, 'caractéris' offset={idx2}")
        log.info(f"  texte complet (2000 der. car.) : {full_text[-2000:]!r}")
        page.close()

        # Lely : re-essayer le clic
        page = browser.new_page(user_agent=UA)
        page.goto("https://www.lely.com/fr/solutions/traite/astronaut/", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        for _ in range(10):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(300)
        tables = page.query_selector_all("table")
        log.info(f"\n=== Lely Astronaut (après scroll) : {len(tables)} table(s) ===")
        for t in tables[:2]:
            rows = t.query_selector_all("tr")
            for r in rows[:8]:
                cells = r.query_selector_all("td, th")
                log.info(f"    row: {[c.inner_text().strip()[:30] for c in cells]}")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
