"""
Script de sondage temporaire — à supprimer après usage.
Round 3 : round 2 a trouvé un lien Issuu sur la page Same
("product_range_same_2026_fr" — catalogue gamme complète). On recherche
TOUS les liens issuu/catalogue/brochure/pdf (pas juste les 40 premiers) sur
les deux accueils, et on inspecte la page Issuu elle-même pour voir si on
peut en extraire du texte/tableaux exploitables (téléchargement direct,
lecteur avec texte sélectionnable, etc.).
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

KEYWORDS = ["issuu", "catalog", "catalogue", "brochure", ".pdf", "product_range", "product-range"]


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

        issuu_urls = []
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

            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            uniq = sorted(set(hrefs))
            matches = [h for h in uniq if any(k in h.lower() for k in KEYWORDS)]
            log.info(f"  {len(uniq)} liens au total, {len(matches)} correspondant aux mots-clés :")
            for u in matches:
                log.info(f"    {u}")
                if "issuu.com" in u.lower():
                    issuu_urls.append((brand, u))

        # Inspecter la/les page(s) Issuu trouvée(s).
        for brand, url in issuu_urls:
            log.info(f"\n{'='*70}\nInspection Issuu ({brand}) : {url}")
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
            except Exception as e:
                log.warning(f"  Page Issuu inaccessible : {e}")
                continue

            # Chercher un bouton/lien de téléchargement.
            download_links = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
            )
            dl_candidates = [d for d in download_links if "download" in d["href"].lower() or "télécharger" in d["text"].lower() or "download" in d["text"].lower()]
            log.info(f"  Liens de téléchargement potentiels : {len(dl_candidates)}")
            for d in dl_candidates[:10]:
                log.info(f"    {d}")

            # Voir si le contenu du document est du texte sélectionnable dans le DOM
            # (lecteur Issuu basé sur des images vs texte réel).
            body_text_len = len(page.evaluate("document.body.innerText"))
            log.info(f"  Longueur du texte visible dans le DOM : {body_text_len} caractères")
            page_count = page.evaluate(
                "document.querySelectorAll('[class*=\"page\"]').length"
            )
            log.info(f"  Éléments avec classe contenant 'page' : {page_count}")

        browser.close()


if __name__ == "__main__":
    main()
