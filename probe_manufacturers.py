"""
Script de sondage temporaire — à supprimer après usage.
Lot 2 round 5 :
- Bogballe : trouver le vrai conteneur de specs (texte en blocs comme Horsch)
- Sky Agriculture (ex-Sulky) : fiche produit DX20 (sous fertilisation/)
- Berthoud.com : fiche produit Vega (gamme grandes cultures, URLs plates)
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
    for text in ["Tout accepter", "Accepter tout", "Accept all", "J'accepte", "Accepter", "Allow all cookies"]:
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
        tables = page.query_selector_all("table")
        log.info(f"    {len(tables)} table(s)")
        for i, t in enumerate(tables[:2]):
            rows = t.query_selector_all("tr")
            for r in rows[:6]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
        # chercher le conteneur autour d'un texte connu
        try:
            loc = page.get_by_text("Largeur de travail", exact=False).first
            if loc.count() if hasattr(loc, "count") else True:
                cls = loc.evaluate("el => el.closest('[class]') ? el.closest('[class]').className : null")
                log.info(f"    classe du plus proche ancêtre de 'Largeur de travail' : {cls!r}")
                parent_text = loc.evaluate("el => { let p = el; for (let i=0;i<4 && p.parentElement;i++) p = p.parentElement; return p.innerText.slice(0, 500); }")
                log.info(f"    texte du grand-parent (500 car.) : {parent_text!r}")
        except Exception as e:
            log.info(f"    pas de 'Largeur de travail' trouvé ({e})")
        text = page.inner_text("body")
        log.info(f"    body text (1000 car.) : {text[:1000]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.bogballe.com/fr/epandeurs-dengrais/modeles/m60w-plus/", "Bogballe M60W-Plus (round2)")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://sky-agriculture.com/produits/fertilisation/dx20/", "Sky Agriculture DX20")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.berthoud.com/vega/", "Berthoud Vega")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
