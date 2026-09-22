"""
Script de sondage temporaire — à supprimer après usage.
Lot 8, round 3 : Same a 0 table mais 55 éléments "spec-like" sur une
fiche produit réelle -> dumper leur contenu pour comprendre la structure.
Rauch (0 table/0 spec-like) et Lely (0 table/0 spec-like) : dernière
vérification sur une 2e fiche avant abandon définitif.
Sulky : domaine injoignable sur 5 variantes d'URL -> abandon confirmé,
pas de round supplémentaire.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def dump_same_specs(page):
    url = "https://www.same-tractors.com/en-gb/tractors/virtus"
    log.info(f"\n===== Same specs : {url} =====")
    page.goto(url, timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    for _ in range(8):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(300)

    specish = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], [class*='donnee' i]")
    log.info(f"  Éléments spec-like : {len(specish)}")
    for i, el in enumerate(specish[:8]):
        cls = el.get_attribute("class") or ""
        tag = el.evaluate("e => e.tagName")
        txt = el.inner_text()
        log.info(f"  --- elt {i} <{tag} class=\"{cls}\"> ({len(txt)} car.) ---")
        log.info("  " + txt[:500].replace("\n", " | "))


def inspect_second_page(page, url, label):
    log.info(f"\n===== {label} (2e fiche) : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        tables = page.query_selector_all("table")
        specish = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], [class*='donnee' i]")
        log.info(f"  Titre: {page.title()}")
        log.info(f"  Tables: {len(tables)} | Éléments spec-like: {len(specish)}")
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

        dump_same_specs(page)
        inspect_second_page(page, "https://rauch.de/duengerstreuer/scheibenstreuer/anbaustreuer/axis-m.html", "Rauch")
        inspect_second_page(page, "https://www.lely.com/fr/solutions/alimentation/vector/", "Lely")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
