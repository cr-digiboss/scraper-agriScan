"""
Script de sondage temporaire — à supprimer après usage.
Round 2 :
- Deutz-Fahr : vérifier le format specs sur une fiche série (serie-9-stage-5).
- Mahindra : mahindratractor.com est le site indien (prix roupies, "Duniya
  Vich Ikko Lalkaar" en pendjabi) — pas pertinent pour un catalogue France/
  Europe. Chercher un site Mahindra Europe/France.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def inspect_deutzfahr(page, url):
    log.info(f"\n===== Deutz-Fahr : {url} =====")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        title = page.title()
        tables = page.query_selector_all("table")
        log.info(f"  Titre : {title}")
        log.info(f"  Tables : {len(tables)}")
        for i, t in enumerate(tables[:4]):
            rows = t.query_selector_all("tr")
            log.info(f"  --- Table {i} ({len(rows)} lignes) ---")
            for row in rows[:6]:
                cells = row.query_selector_all("td, th")
                texts = [c.inner_text().strip().replace("\n", " ") for c in cells]
                log.info("    " + " | ".join(texts))
        specish = page.query_selector_all("[class*='spec' i]")
        log.info(f"  Éléments class*=spec : {len(specish)}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        model_links = sorted(set(
            h.split("?")[0].split("#")[0] for h in hrefs
            if "deutz-fahr.com/fr-fr/tracteurs/" in h
        ))
        log.info(f"  Sous-liens tracteurs sur cette page : {len(model_links)}")
        for m in model_links[:20]:
            log.info(f"    {m}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


def try_url(page, label, url):
    log.info(f"\n===== {label} : {url} =====")
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        log.info(f"  OK — Titre : {page.title()} — URL finale : {page.url}")
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

        inspect_deutzfahr(page, "https://www.deutz-fahr.com/fr-fr/tracteurs/serie-9-stage-5")

        log.info("\n===== Recherche Mahindra Europe =====")
        for label, url in [
            ("mahindra.eu", "https://www.mahindra.eu/"),
            ("mahindra-agri.eu", "https://www.mahindra-agri.eu/"),
            ("eu.mahindra.com", "https://eu.mahindra.com/"),
            ("mahindratractors.eu", "https://www.mahindratractors.eu/"),
            ("mahindra.com agri", "https://www.mahindra.com/farm-equipment"),
        ]:
            try_url(page, label, url)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
