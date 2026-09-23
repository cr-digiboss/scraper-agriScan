"""
Script de sondage temporaire — à supprimer après usage.
Lot 9, round 6 (dernier avant décisions) :
- Merlo abandonné (3 tentatives infructueuses : mauvaises URLs, titre
  "404" persistant, navigation par clic qui timeout).
- Monosem : dump texte complet de la page NG Plus pour chercher un
  format specs non-tabulaire (comme découvert pour Kubota).
- Pellenc : extraire tous les liens internes de la page vendange
  filtrés sur des chemins plus profonds (fiches modèles individuelles).
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def dump_monosem_text(page, url):
    log.info(f"\n===== Monosem texte complet : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(12):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        body_text = page.inner_text("body")
        log.info(f"  Longueur texte body : {len(body_text)}")
        log.info("  --- Texte (2500 premiers caractères) ---")
        log.info("  " + body_text[:2500].replace("\n", " | "))
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def dump_pellenc_deep_links(page, url):
    log.info(f"\n===== Pellenc liens profonds : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(12):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs))
        deep = [s for s in seen if "/nos-produits/de-la-vigne-a-la-cave/viticulture/" in s
                and s.rstrip("/") != url.rstrip("/")]
        log.info(f"  Liens profonds sous cette catégorie : {len(deep)}")
        for s in deep:
            log.info(f"    {s}")
        tables = page.query_selector_all("table")
        log.info(f"  Tables : {len(tables)}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            viewport={"width": 1280, "height": 1600},
        )
        page = context.new_page()

        dump_monosem_text(page, "https://www.monosem.fr/semoirs-de-precision/semoir-monograine/semoir-pneumatique/ng-plus-ng-plus-e/")
        dump_pellenc_deep_links(page, "https://www.pellenc.com/fr-fr/nos-produits/de-la-vigne-a-la-cave/viticulture/machine-a-vendanger-et-multifonction-vignes-larges")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
