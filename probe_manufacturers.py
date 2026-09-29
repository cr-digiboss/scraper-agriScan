"""
Script de sondage temporaire — à supprimer après usage.
Lot 3 round 3 :
- Hardi/Tecnoma/Agrifac : chercher un onglet/lien "Caractéristiques" ou
  "Spécifications techniques" plus bas sur la page (comme Berthoud)
- Lely : fiche produit Astronaut (robot de traite) pour voir s'il y a des
  specs structurées
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CANDIDATE_TEXTS = [
    "Caractéristiques techniques", "Caractéristiques", "Spécifications techniques",
    "Spécifications", "Données techniques", "Fiche technique", "Technical specifications",
]


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


def inspect(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1500)
        log.info(f"\n--- {label} : {url} title={page.title()!r}")

        body_text_full = page.inner_text("body")
        log.info(f"    longueur texte page : {len(body_text_full)} caractères")

        for text in CANDIDATE_TEXTS:
            idx = body_text_full.find(text)
            if idx >= 0:
                log.info(f"    trouvé '{text}' à l'offset {idx}")

        for text in CANDIDATE_TEXTS:
            try:
                loc = page.get_by_text(text, exact=False).first
                if loc.count() == 0:
                    continue
                loc.scroll_into_view_if_needed(timeout=3000)
                loc.click(timeout=3000)
                page.wait_for_timeout(2000)
                tables = page.query_selector_all("table")
                log.info(f"    après clic sur '{text}' : {len(tables)} table(s)")
                for t in tables[:2]:
                    rows = t.query_selector_all("tr")
                    for r in rows[:6]:
                        cells = r.query_selector_all("td, th")
                        log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
                if tables:
                    break
            except Exception:
                continue
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://hardi.com/fr/sprayers/mounted/master", "Hardi Master")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.tecnoma.com/produits/pulverisateur-agricoles/pulverisateur-porte/premis/", "Tecnoma Premis")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.agrifac.com/fr/pulverisateurs/vanguard-55/", "Agrifac Vanguard 55")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.lely.com/fr/solutions/traite/astronaut/", "Lely Astronaut")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
