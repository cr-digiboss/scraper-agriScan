"""
Script de sondage temporaire — à supprimer après usage.
Lot 6, round 2 : depuis une page catégorie, trouver les liens produits,
puis ouvrir une fiche produit et chercher un tableau de specs.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

CATEGORY_URLS = {
    "Amazone": "https://amazone.fr/fr-fr/produits-et-solutions-digitales/machines-agricoles/travail-du-sol/charrues",
    "Kuhn": "https://www.kuhn.fr/grande-culture/materiels-de-travail-du-sol",
}


def collect_links(page, netloc_hint):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = []
    seen = set()
    for href in hrefs:
        u = urlparse(href)
        if netloc_hint not in u.netloc:
            continue
        clean = href.split("?")[0].split("#")[0]
        if clean in seen or not clean:
            continue
        seen.add(clean)
        links.append(clean)
    return links


def inspect_product_page(page, url):
    log.info(f"    -> ouverture fiche : {url}")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"       Titre: {title}")
        log.info(f"       Tables trouvées: {len(tables)}")
        for i, t in enumerate(tables[:3]):
            txt = t.inner_text()
            log.info(f"       --- table {i} ({len(txt)} car.) ---")
            log.info("       " + txt[:400].replace("\n", " | "))
        if not tables:
            specish = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], [class*='donnee' i]")
            log.info(f"       Éléments spec-like (sans table): {len(specish)}")
            for i, el in enumerate(specish[:3]):
                cls = el.get_attribute("class") or ""
                txt = el.inner_text()
                log.info(f"       --- elt {i} class=\"{cls}\" ({len(txt)} car.) ---")
                log.info("       " + txt[:400].replace("\n", " | "))
    except Exception as e:
        log.info(f"       ERREUR : {e!r}")


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

        for brand, url in CATEGORY_URLS.items():
            log.info(f"\n===== {brand} catégorie : {url} =====")
            page = context.new_page()
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                for _ in range(6):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(300)
                netloc_hint = urlparse(url).netloc.replace("www.", "")
                links = collect_links(page, netloc_hint)
                log.info(f"  Liens internes uniques : {len(links)}")
                base_path = urlparse(url).path
                candidates = [l for l in links if urlparse(l).path != base_path and urlparse(l).path.startswith(base_path)]
                log.info(f"  Candidats sous-chemin ({base_path}) : {len(candidates)}")
                for c in candidates[:15]:
                    log.info(f"    {c}")
                if candidates:
                    inspect_product_page(page, candidates[0])
                    if len(candidates) > 1:
                        inspect_product_page(page, candidates[1])
            except Exception as e:
                log.info(f"  ERREUR : {e!r}")
            finally:
                page.close()

        browser.close()


if __name__ == "__main__":
    main()
