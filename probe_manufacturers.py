"""
Script de sondage temporaire — à supprimer après usage.
Diagnostique pourquoi scrape_mchale trouve 40 fiches produit mais en
extrait 0 machine : dump la structure réelle d'une fiche produit McHale
(tables, classes contenant "spec"/"technical", texte brut) pour voir
pourquoi le sélecteur actuel ([class*='spec' i], [class*='technical' i])
ne matche rien. Ne touche pas à la base de données.
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

MCHALE_HOME = "https://www.mchale.net/"


def find_product_links(page) -> list:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "mchale.net" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 2 and segments[0] == "products":
            links.add(href.split("?")[0].split("#")[0])
    return sorted(links)


def probe_product(page, url):
    log.info(f"\n{'=' * 80}\n{url}\n{'=' * 80}")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(400)

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")

        spec_els = page.query_selector_all("[class*='spec' i], [class*='technical' i]")
        log.info(f"Éléments [class*=spec/technical] : {len(spec_els)}")

        # Cherche tout élément dont le texte contient un mot-clé de section specs
        all_els = page.query_selector_all("h1, h2, h3, h4, div, section")
        keyword_hits = []
        for el in all_els[:400]:
            try:
                txt = el.inner_text().strip()
            except Exception:
                continue
            if txt and len(txt) < 60 and any(
                kw in txt.lower() for kw in ["technical", "specification", "spec", "dimensions", "données"]
            ):
                cls = el.get_attribute("class") or ""
                tag = el.evaluate("e => e.tagName")
                keyword_hits.append((tag, cls[:80], txt[:60]))

        log.info(f"Titres/blocs contenant un mot-clé specs : {len(keyword_hits)}")
        for tag, cls, txt in keyword_hits[:15]:
            log.info(f"  <{tag} class=\"{cls}\"> {txt}")

        # Cherche des liens PDF (fiche technique en téléchargement)
        pdf_links = page.eval_on_selector_all(
            "a[href$='.pdf']", "els => els.map(e => e.href)"
        )
        log.info(f"Liens PDF : {len(pdf_links)}")
        for l in pdf_links[:5]:
            log.info(f"  {l}")

    except Exception as e:
        log.error(f"Erreur sur {url} : {e}")


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

        page.goto(MCHALE_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        links = find_product_links(page)
        log.info(f"Liens produit trouvés : {len(links)}")

        # Un produit qui marchait déjà (baler) + deux qui ne marchaient pas
        # a priori (autres catégories), pour comparer.
        for url in links[:4]:
            probe_product(page, url)

        browser.close()


if __name__ == "__main__":
    main()
