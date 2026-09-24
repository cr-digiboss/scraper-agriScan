"""
Script de sondage temporaire — à supprimer après usage.
Güttler, complétude round 3 : pour chacune des 23 URLs produit allemandes
du sitemap, vérifier s'il existe une version française correspondante
(lien hreflang / sélecteur de langue), et comparer avec les 12 URLs
françaises déjà connues via /fr/produits/.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

DE_URLS = [
    "https://guttler.org/produkt/avant/",
    "https://guttler.org/produkt/duplex/",
    "https://guttler.org/produkt/feldmeister-lk-30-40-45/",
    "https://guttler.org/produkt/feldmeister/",
    "https://guttler.org/produkt/greenmaster-250-300/",
    "https://guttler.org/produkt/greenmaster-600-750-800/",
    "https://guttler.org/produkt/greenmaster-compact-600/",
    "https://guttler.org/produkt/greenmaster-ecoline-600/",
    "https://guttler.org/produkt/greenmaster-zinkensaat/",
    "https://guttler.org/produkt/greenmaster/",
    "https://guttler.org/produkt/master-640-770-820/",
    "https://guttler.org/produkt/master-und-magnum/",
    "https://guttler.org/produkt/mastercut-600/",
    "https://guttler.org/produkt/matador/",
    "https://guttler.org/produkt/mayor-640-770-820/",
    "https://guttler.org/produkt/mediana/",
    "https://guttler.org/produkt/offset-480-640/",
    "https://guttler.org/produkt/primusplus-300/",
    "https://guttler.org/produkt/super-maxx-1000-1200-7-bio/",
    "https://guttler.org/produkt/super-maxx-bio/",
    "https://guttler.org/produkt/super-maxx-culti-sem/",
    "https://guttler.org/produkt/super-maxx-culti/",
    "https://guttler.org/produkt/super-maxx-heavy-duty/",
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for url in DE_URLS:
            try:
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(500)
            except Exception as e:
                log.info(f"{url} → ERREUR {e}")
                continue

            hreflangs = page.eval_on_selector_all(
                "link[rel='alternate'][hreflang]",
                "els => els.map(e => ({lang: e.getAttribute('hreflang'), href: e.href}))",
            )
            fr = [h for h in hreflangs if h["lang"] == "fr" or h["lang"].startswith("fr-")]
            if fr:
                log.info(f"{url}\n  FR → {fr[0]['href']}")
            else:
                # chercher un lien de sélecteur de langue dans la page
                switcher = page.eval_on_selector_all(
                    "a[href*='/fr/']",
                    "els => els.map(e => e.href).slice(0,3)",
                )
                if switcher:
                    log.info(f"{url}\n  FR (via lien) → {switcher}")
                else:
                    log.info(f"{url}\n  PAS DE VERSION FR TROUVÉE")

        browser.close()


if __name__ == "__main__":
    main()
