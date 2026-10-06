"""
Script de sondage temporaire — à supprimer après usage.
Round 4 : aucun PDF/catalogue sur les accueils (Deutz-Fahr : rien du tout ;
Same : un catalogue Issuu mais basé sur des images, sans texte extractible
ni bouton de téléchargement). Les PDF techniques sont généralement liés
depuis les FICHES PRODUIT, pas l'accueil. On ouvre le menu principal pour
trouver une vraie page catégorie "tracteurs", puis on inspecte une fiche
produit individuelle à la recherche d'un bouton brochure/fiche technique.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

SITES = {
    "Deutz-Fahr": "https://www.deutz-fahr.com/fr-fr",
    "Same": "https://www.same-tractors.com/fr-fr",
}


def accept_cookies(page):
    for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')", "button:has-text('Accepter')"]:
        try:
            btn = page.query_selector(sel)
            if btn:
                btn.click(force=True, timeout=3000)
                page.wait_for_timeout(1500)
                return
        except Exception:
            pass


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        for brand, home in SITES.items():
            log.info(f"\n{'='*70}\n{brand} — {home}")
            try:
                page.goto(home, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
            except Exception as e:
                log.warning(f"  Accueil inaccessible : {e}")
                continue
            accept_cookies(page)
            page.wait_for_timeout(2000)

            # Chercher et cliquer sur le bouton menu principal (hamburger ou nav).
            menu_info = page.evaluate(
                """
                () => {
                    const keywords = ['menu', 'nav-toggle', 'hamburger', 'burger'];
                    const found = {};
                    keywords.forEach(k => {
                        const els = document.querySelectorAll(`[class*="${k}"], [id*="${k}"]`);
                        if (els.length) found[k] = els.length;
                    });
                    return found;
                }
                """
            )
            log.info(f"  Éléments menu potentiels : {menu_info}")

            for sel in ["[class*='menu-toggle']", "[class*='hamburger']", "button[aria-label*='menu' i]", "nav button"]:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click(force=True, timeout=3000)
                        log.info(f"  Menu ouvert via {sel!r}")
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass

            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            uniq = sorted(set(hrefs))
            log.info(f"  {len(uniq)} liens après tentative d'ouverture du menu")
            # Chercher spécifiquement des mots clés de catégories produit.
            cat_kw = ["tracteur", "tractor", "moissonneuse", "produit", "product", "range", "gamme"]
            cat_links = [h for h in uniq if any(k in h.lower() for k in cat_kw)]
            for u in cat_links:
                log.info(f"    {u}")

        browser.close()


if __name__ == "__main__":
    main()
