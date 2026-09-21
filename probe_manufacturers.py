"""
Script de sondage temporaire — à supprimer après usage.
Lot 7, round 2 :
- Valtra, JCB, Bednar : catégorie -> fiche produit -> table specs
- Grégoire Besson : fiche produit directe (petit catalogue) -> table specs
- Manitou, Maschio Gaspardo, Rabe : correction d'URL (round 1 en échec)
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


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


def inspect_product_page(page, url, label=""):
    log.info(f"    -> ouverture fiche {label}: {url}")
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
        for i, t in enumerate(tables[:2]):
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


def try_category(page, brand, category_url):
    log.info(f"\n===== {brand} catégorie : {category_url} =====")
    try:
        page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        netloc_hint = urlparse(category_url).netloc.replace("www.", "")
        links = collect_links(page, netloc_hint)
        base_path = urlparse(category_url).path
        candidates = [l for l in links if urlparse(l).path.rstrip("/") != base_path.rstrip("/") and urlparse(l).path.startswith(base_path)]
        log.info(f"  Candidats sous-chemin : {len(candidates)}")
        for c in candidates[:10]:
            log.info(f"    {c}")
        if candidates:
            inspect_product_page(page, candidates[0])
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def try_direct(page, brand, url):
    log.info(f"\n===== {brand} (retry) : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        title = page.title()
        html_len = len(page.content())
        log.info(f"  Titre : {title}")
        log.info(f"  Longueur HTML : {html_len}")
        netloc_hint = urlparse(url).netloc.replace("www.", "")
        links = collect_links(page, netloc_hint)
        log.info(f"  Liens internes uniques : {len(links)}")
        for l in links[:20]:
            log.info(f"    {l}")
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

        try_category(page, "Valtra", "https://www.valtra.fr/produits/serief.html")
        try_category(page, "JCB", "https://www.jcb.com/fr-FR/products/machines/tracteurs/")
        try_category(page, "Bednar", "https://www.bednar.com/fr/semoirs/")
        inspect_product_page(page, "https://www.gregoire-besson.com/fr/machines/prima", "Grégoire Besson")

        try_direct(page, "Manitou", "https://www.manitou.com/fr-FR")
        try_direct(page, "Maschio Gaspardo", "https://www.maschio.com/fr/")
        try_direct(page, "Rabe", "https://www.rabe.de/")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
