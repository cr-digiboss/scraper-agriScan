"""
Script de sondage temporaire — à supprimer après usage.
Lot 9, round 5 :
- Monosem : vraie fiche modèle semoir (ng-plus-4-4e) — format specs ?
- Pellenc : vraie sous-catégorie produit (machine à vendanger) — liens
  fiches modèles + format specs ?
- Merlo : le <title> "404" apparaît même sur de vrais liens internes
  (site JS qui ne s'hydrate peut-être pas assez vite avec un goto
  direct). Test : naviguer depuis la page d'accueil puis cliquer sur le
  lien réel (navigation interne JS) au lieu d'un goto direct.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect(page, label, url):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre : {title} — URL finale : {page.url}")
        log.info(f"  Tables : {len(tables)}")
        for i, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"  --- Table {i} ({len(rows)} lignes) ---")
            for row in rows[:8]:
                cells = row.query_selector_all("td, th")
                texts = [c.inner_text().strip().replace("\n", " ") for c in cells]
                log.info("    " + " | ".join(texts))
        divtables = page.query_selector_all("[class*='table' i]")
        log.info(f"  Éléments class*=table : {len(divtables)}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs))
        log.info(f"  Liens : {len(seen)} (20 premiers)")
        for s in seen[:20]:
            log.info(f"    {s}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def test_merlo_click_navigation(page):
    log.info("\n===== Merlo : navigation par clic depuis l'accueil =====")
    try:
        page.goto("https://www.merlo.com/fr/fr/", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        link = page.query_selector("a[href*='chariots-telescopiques-electriques']")
        if not link:
            log.info("  Lien vers chariots-telescopiques-electriques introuvable sur l'accueil")
            return
        link.click()
        page.wait_for_timeout(4000)
        title = page.title()
        log.info(f"  Après clic — Titre : {title} — URL : {page.url}")
        tables = page.query_selector_all("table")
        log.info(f"  Tables : {len(tables)}")
        specish = page.query_selector_all("[class*='spec' i]")
        log.info(f"  Éléments class*=spec : {len(specish)}")
        for el in specish[:5]:
            log.info("    " + el.inner_text().strip().replace("\n", " | ")[:300])
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

        inspect(page, "Monosem NG Plus 4-4E",
               "https://www.monosem.fr/semoirs-de-precision/semoir-monograine/semoir-pneumatique/ng-plus-4-4e/")
        inspect(page, "Pellenc machine à vendanger",
               "https://www.pellenc.com/fr-fr/nos-produits/de-la-vigne-a-la-cave/viticulture/machine-a-vendanger-et-multifonction-vignes-larges")
        test_merlo_click_navigation(page)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
