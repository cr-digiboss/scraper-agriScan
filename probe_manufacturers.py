"""
Script de sondage temporaire — à supprimer après usage.
Lot 5, round 2 : vérifie la présence de tableaux HTML de specs sur des
fiches produit concrètes (Grimme, Väderstad), creuse un niveau
supplémentaire pour Lemken/Horsch (catégorie -> produit), retente Krone
avec un timeout court, et corrige l'URL Vicon (redirige vers ien.vicon.eu).
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def probe_product(page, name, url):
    log.info(f"\n{'=' * 80}\n{name} (fiche produit) — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=20000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(4000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(400)

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")
        for i, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            for r in rows[:4]:
                log.info(f"    {r.inner_text().replace(chr(10), ' | ')[:150]}")

        spec_els = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='daten' i]")
        log.info(f"Éléments [class*=spec/technical/daten] : {len(spec_els)}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


def probe_category(page, name, url):
    log.info(f"\n{'=' * 80}\n{name} (catégorie) — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=20000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(4000)
        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(400)

        hrefs = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        final_domain = urlparse(page.url).netloc
        root_domain = ".".join(final_domain.split(".")[-2:])
        base_path = urlparse(page.url).path.rstrip("/")

        deeper = []
        for l in hrefs:
            u = urlparse(l["href"])
            if root_domain not in l["href"] or not l["text"]:
                continue
            if u.path.rstrip("/").startswith(base_path) and u.path.rstrip("/") != base_path:
                deeper.append(l)

        seen = set()
        uniq = []
        for l in deeper:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)

        log.info(f"Liens plus profonds que la catégorie actuelle : {len(uniq)}")
        for l in uniq[:15]:
            log.info(f"  [{l['text'][:50]:50}] {l['href']}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


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

        # Fiches produit trouvées au round 1
        probe_product(page, "Grimme", "https://products.grimme.com/fr/p/cs-150")
        probe_product(page, "Vaderstad", "https://www.vaderstad.com/fr/travail-du-sol/outils-de-travail-du-sol/opus")

        # Un niveau plus profond pour Lemken/Horsch
        probe_category(page, "Lemken", "https://lemken.com/fr-fr/machines-agricoles/travail-du-sol/labour")
        probe_category(page, "Horsch", "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques")

        # Retry Krone avec timeout court
        probe_category(page, "Krone", "https://www.krone.de/fr/")

        # Vicon : bonne URL trouvée au round 1
        probe_category(page, "Vicon", "https://ien.vicon.eu/choppers/flail-choppers")

        browser.close()


if __name__ == "__main__":
    main()
