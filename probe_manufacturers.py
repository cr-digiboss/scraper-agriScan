"""
Script de sondage temporaire — à supprimer après usage.
Case IH / Kubota, round 3 :
- Case IH : dumper le contenu des 7 éléments "spec-like" trouvés sur une
  fiche produit (0 table classique) pour voir si des données chiffrées
  sont exploitables.
- Kubota : explorer /fr/ag (agriculture) pour trouver la structure
  catégorie -> produit.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def dump_caseih_specs(page):
    url = "https://www.caseih.com/fr-fr/france/produits/tracteurs/magnum-serie"
    log.info(f"\n===== Case IH specs : {url} =====")
    page.goto(url, timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    for _ in range(8):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(300)

    specish = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], [class*='donnee' i]")
    log.info(f"  Éléments spec-like : {len(specish)}")
    for i, el in enumerate(specish):
        cls = el.get_attribute("class") or ""
        tag = el.evaluate("e => e.tagName")
        txt = el.inner_text()
        log.info(f"  --- elt {i} <{tag} class=\"{cls}\"> ({len(txt)} car.) ---")
        log.info("  " + txt[:500].replace("\n", " | "))


def explore_kubota(page):
    url = "https://www.kubota-eu.com/fr/ag"
    log.info(f"\n===== Kubota Agriculture : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        log.info(f"  Titre : {title}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = set()
        samples = []
        for href in hrefs:
            u = urlparse(href)
            if "kubota-eu.com" not in u.netloc:
                continue
            clean = href.split("?")[0].split("#")[0]
            if clean in seen:
                continue
            seen.add(clean)
            samples.append(clean)
        log.info(f"  Liens internes uniques : {len(samples)}")
        for s in samples[:40]:
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

        dump_caseih_specs(page)
        explore_kubota(page)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
