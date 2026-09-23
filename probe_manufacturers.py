"""
Script de sondage temporaire — à supprimer après usage.
Lot 9, round 2 : approfondissement par marque.
- Horsch : fiche catégorie travail-du-sol/dechaumeur-a-disques (specs ?)
- Krone : fiche modèle easycut-f (specs ?)
- Merlo : fiche modèle ew25-5 (specs ?)
- Monosem : cibler monosem.fr directement
- Pellenc : chercher la bonne URL (pellenc.com racine, ou autre domaine)
- Joskin : fiche catégorie épandeurs-de-lisier (liens modèles ?)
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
            for row in rows[:6]:
                cells = row.query_selector_all("td, th")
                texts = [c.inner_text().strip().replace("\n", " ") for c in cells]
                log.info("    " + " | ".join(texts))
        specish = page.query_selector_all("[class*='spec' i]")
        log.info(f"  Éléments class*=spec : {len(specish)}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs))
        log.info(f"  Liens uniques : {len(seen)} (30 premiers)")
        for s in seen[:30]:
            log.info(f"    {s}")
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

        inspect(page, "Horsch dechaumeur-a-disques", "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques")
        inspect(page, "Krone easycut-f", "https://www.krone.fr/produits/faucheuses-a-disques/easycut-f")
        inspect(page, "Merlo ew25-5", "https://www.merlo.com/fr/fr/p/chariots-telescopiques/chariots-telescopiques-electriques/ew25-5/")
        inspect(page, "Monosem.fr", "https://www.monosem.fr/")
        inspect(page, "Pellenc racine", "https://www.pellenc.com/")
        inspect(page, "Joskin épandeurs-de-lisier", "https://www.joskin.com/fr/%C3%A9pandeurs-de-lisier")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
