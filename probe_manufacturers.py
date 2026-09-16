"""
Script de sondage temporaire — à supprimer après usage.
Lot 3, round 2 : vérifie les specs sur des fiches modèles déjà identifiées
(Same, Landini, McCormick), cherche des fiches modèles plus profondes pour
Bednar, et corrige les URLs de départ pour Kubota et Maschio Gaspardo.
Ne touche pas à la base de données.
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

PRODUCT_PAGES = {
    "Same (Virtus)": "https://www.same-tractors.com/fr-fr/tracteurs/virtus",
    "Landini (Serie 6RS, IT)": "https://landini-tractors.com/it/it/prodotti/serie-6rs.html",
    "McCormick (X8 VT-Drive)": "https://mccormick-tractors.com/fr/fr/produits/x8-vt-drive.html",
}

CATEGORY_PAGES = {
    "Bednar (Semoirs)": "https://www.bednar.com/fr/semoirs/",
}

SITES_RETRY = {
    "Kubota": "https://www.kubota-eu.com/",
    "Maschio Gaspardo": "https://www.maschionet.com/",
}


def probe_product(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(5):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(600)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")
        for i, t in enumerate(tables[:4]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            for r in rows[:2]:
                log.info(f"    ligne : {r.inner_text().replace(chr(10), ' | ')[:180]}")

        dls = page.query_selector_all("dl")
        log.info(f"Nombre de <dl> : {len(dls)}")
        if dls:
            log.info(f"    échantillon : {dls[0].inner_text()[:250].replace(chr(10), ' | ')}")

        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], "
            "[class*='fiche-technique' i], [class*='donnees-techniques' i], [class*='dati-tecnici' i]"
        )
        log.info(f"Éléments classe spec/technical : {len(spec_divs)}")
        for d in spec_divs[:3]:
            txt = d.inner_text().strip().replace("\n", " | ")
            if txt:
                log.info(f"    échantillon : {txt[:250]}")

        pdf_links = page.eval_on_selector_all("a[href*='.pdf' i]", "els => els.map(e => e.href)")
        log.info(f"PDF trouvés : {len(pdf_links)}")
        for p in pdf_links[:3]:
            log.info(f"    {p}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


def probe_category(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)

        links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        final_domain = urlparse(page.url).netloc
        root_domain = ".".join(final_domain.split(".")[-2:])
        base_path = urlparse(page.url).path.rstrip("/")

        deeper = []
        for l in links:
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

        log.info(f"Liens plus profonds que la page actuelle : {len(uniq)}")
        for l in uniq[:30]:
            log.info(f"  [{l['text'][:55]:55}] {l['href']}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


def probe_site(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} (retry) — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        final_domain = urlparse(page.url).netloc
        root_domain = ".".join(final_domain.split(".")[-2:])
        internal = [l for l in links if root_domain in l["href"] and l["text"]]
        seen = set()
        uniq = []
        for l in internal:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)

        log.info(f"Domaine racine utilisé pour filtrer : {root_domain}")
        log.info(f"Liens internes uniques trouvés : {len(uniq)} (échantillon des 60 premiers)")
        for l in uniq[:60]:
            log.info(f"  [{l['text'][:55]:55}] {l['href']}")

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
        for name, url in PRODUCT_PAGES.items():
            probe_product(name, url, page)
        for name, url in CATEGORY_PAGES.items():
            probe_category(name, url, page)
        for name, url in SITES_RETRY.items():
            probe_site(name, url, page)
        browser.close()


if __name__ == "__main__":
    main()
