"""
Script de sondage temporaire — à supprimer après usage.
Lot 7, round 3 :
- Valtra, Bednar : la page catégorie n'a pas donné de candidats sous-chemin
  -> chercher des tables directement sur la page catégorie, et dumper
  tous les liens (pas seulement sous-chemin) pour trouver le vrai pattern.
- Manitou : catégorie -> fiche produit -> table
- Maschio Gaspardo : debug pourquoi 0 liens malgré HTML de 1.3 Mo
- Grégoire Besson : 2e fiche produit (prima = 0 table), pour confirmer
  abandon ou trouver le vrai emplacement des specs
- Rabe : abandonné (rabe.de = site sans rapport, marque absorbée par
  Väderstad — pas de round supplémentaire)
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def dump_all_links_and_tables(page, url, label):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        log.info(f"  Titre : {title}")
        tables = page.query_selector_all("table")
        log.info(f"  Tables sur cette page : {len(tables)}")
        for i, t in enumerate(tables[:2]):
            txt = t.inner_text()
            log.info(f"  --- table {i} ({len(txt)} car.) ---")
            log.info("  " + txt[:400].replace("\n", " | "))
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        log.info(f"  Total liens bruts (a[href]) : {len(hrefs)}")
        for h in hrefs[:15]:
            log.info(f"    {h}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


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
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        base_path = urlparse(category_url).path
        seen = set()
        candidates = []
        for href in hrefs:
            u = urlparse(href)
            if netloc_hint not in u.netloc:
                continue
            clean = href.split("?")[0].split("#")[0]
            if clean in seen or urlparse(clean).path.rstrip("/") == base_path.rstrip("/"):
                continue
            if not urlparse(clean).path.startswith(base_path):
                continue
            seen.add(clean)
            candidates.append(clean)
        log.info(f"  Candidats sous-chemin : {len(candidates)}")
        for c in candidates[:10]:
            log.info(f"    {c}")
        if candidates:
            inspect_product_page(page, candidates[0])
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

        dump_all_links_and_tables(page, "https://www.valtra.fr/produits/serief.html", "Valtra serie F (page complète)")
        dump_all_links_and_tables(page, "https://www.bednar.com/fr/semoirs/", "Bednar semoirs (page complète)")
        try_category(page, "Manitou", "https://www.manitou.com/fr-FR/nos-machines/chariots-telescopiques")
        dump_all_links_and_tables(page, "https://www.maschio.com/fr/", "Maschio Gaspardo (debug liens)")
        inspect_product_page(page, "https://www.gregoire-besson.com/fr/machines/rover", "Grégoire Besson rover")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
