"""
Script de sondage temporaire — à supprimer après usage.
Deutz-Fahr et Same (plateforme SDF Group partagée, Vue.js SPA) avaient été
abandonnés plus tôt cette session : le tableau de specs structurel existe
dans le DOM mais reste vide (aucune requête réseau, aucun état embarqué).
Avant d'abandonner définitivement, on vérifie s'il existe des PDF
téléchargeables (brochures/fiches techniques) sur les fiches produit, sur
le modèle de ce qui a marché pour Monosem.
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


def find_pdf_links(page):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    return sorted({h for h in hrefs if h.lower().split("?")[0].endswith(".pdf")})


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        for brand, home in SITES.items():
            log.info(f"\n{'='*70}\n{brand} — {home}")
            try:
                page.goto(home, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
            except Exception as e:
                log.warning(f"  Accueil inaccessible : {e}")
                continue

            # Accepter les cookies si bannière présente (pattern OneTrust fréquent)
            for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')", "button:has-text('Accepter')"]:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(1000)
                        break
                except Exception:
                    pass

            pdf_home = find_pdf_links(page)
            log.info(f"  PDF sur l'accueil : {len(pdf_home)}")
            for u in pdf_home[:10]:
                log.info(f"    {u}")

            # Chercher les liens vers des pages produit/catégorie pour aller voir
            # une fiche modèle individuelle.
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            product_like = sorted({
                h for h in hrefs
                if brand.lower().replace("-", "") in h.lower().replace("-", "") or True
            })
            category_links = [h for h in hrefs if "/produits/" in h.lower() or "/products/" in h.lower() or "/prodotti/" in h.lower()]
            log.info(f"  Liens 'produits' trouvés : {len(set(category_links))}")
            for u in sorted(set(category_links))[:15]:
                log.info(f"    {u}")

        browser.close()


if __name__ == "__main__":
    main()
