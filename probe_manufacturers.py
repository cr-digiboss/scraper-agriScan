"""
Script de sondage temporaire — à supprimer après usage.
Round 2 : le round 1 n'a trouvé qu'1 lien ("produits") qui était en fait le
lien du bandeau cookies OneTrust lui-même — le reste de la nav n'a pas été
capturé, probablement parce que le bandeau bloque l'affichage/l'interaction
avant qu'on ait fini d'attendre. On dump TOUS les liens de la page (pas de
filtre), avec un délai plus long et une tentative de clic sur le bouton
cookies, pour voir la vraie structure de navigation Deutz-Fahr / Same.
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

            # Essayer plusieurs sélecteurs de bouton cookies, avec force=True.
            for sel in [
                "#onetrust-accept-btn-handler",
                "button:has-text('Accept')",
                "button:has-text('Accepter')",
                "button:has-text('Tout accepter')",
                "[id*='cookie'] button",
            ]:
                try:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click(force=True, timeout=3000)
                        log.info(f"  Cookie banner fermé via {sel!r}")
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    pass

            page.wait_for_timeout(3000)

            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            uniq = sorted(set(hrefs))
            log.info(f"  {len(uniq)} liens <a> au total sur l'accueil")
            same_domain = [h for h in uniq if brand.split("-")[0].lower() in h.lower() or "deutz" in h.lower() or "same" in h.lower()]
            for u in uniq[:40]:
                log.info(f"    {u}")

            pdf_links = [h for h in uniq if h.lower().split("?")[0].endswith(".pdf")]
            log.info(f"  PDF trouvés : {len(pdf_links)}")
            for u in pdf_links:
                log.info(f"    PDF: {u}")

        browser.close()


if __name__ == "__main__":
    main()
