"""
Script de sondage temporaire — à supprimer après usage.
Lot 1 round 3 : structure des pages produit.
- Horsch : catégorie /fr/produits/travail-du-sol -> lister les fiches modèles
- Amazone : catégorie semoirs-monograines -> lister fiches + inspecter une fiche
- Vicon : /produits -> lister fiches + inspecter une fiche
- Maschio Gaspardo : la home renvoie une page "Client Challenge" (anti-bot,
  probablement Cloudflare) -> retest avec un user-agent réaliste
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def dump_links(page, base_url, label):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    netloc = urlparse(base_url).netloc
    same = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if netloc in urlparse(h).netloc))
    log.info(f"  {label} : {len(same)} liens même domaine")
    for h in same[:60]:
        log.info(f"    {h}")


def inspect_product_page(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        log.info(f"\n--- Fiche {label} : {url} title={page.title()!r}")
        tables = page.query_selector_all("table")
        log.info(f"    {len(tables)} table(s) trouvée(s)")
        for i, t in enumerate(tables[:2]):
            rows = t.query_selector_all("tr")
            log.info(f"    table {i}: {len(rows)} lignes")
            for r in rows[:4]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
        text = page.inner_text("body")
        log.info(f"    body text (800 premiers car.) : {text[:800]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Horsch
        page = browser.new_page(user_agent=UA)
        try:
            page.goto("https://www.horsch.com/fr/produits/travail-du-sol", timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            log.info(f"\n=== Horsch catégorie travail-du-sol : title={page.title()!r}")
            dump_links(page, "https://www.horsch.com", "Horsch travail-du-sol")
        except Exception as e:
            log.warning(f"Horsch catégorie : échec ({e})")
        page.close()

        # Amazone
        page = browser.new_page(user_agent=UA)
        try:
            page.goto(
                "https://amazone.fr/fr-fr/produits-et-solutions-digitales/machines-agricoles/semis/semoirs-monograines",
                timeout=25000, wait_until="domcontentloaded",
            )
            page.wait_for_timeout(2500)
            log.info(f"\n=== Amazone catégorie semoirs-monograines : title={page.title()!r}")
            dump_links(page, "https://amazone.fr", "Amazone semoirs-monograines")
        except Exception as e:
            log.warning(f"Amazone catégorie : échec ({e})")
        inspect_product_page(
            page,
            "https://amazone.fr/fr-fr/produits-et-solutions-digitales/machines-agricoles/semis/semoirs-monograines/amazone-semoir-monograine-precea-6000-2cc-475842",
            "Amazone Precea 6000-2CC",
        )
        page.close()

        # Vicon
        page = browser.new_page(user_agent=UA)
        try:
            page.goto("https://fr.vicon.eu/produits", timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            log.info(f"\n=== Vicon /produits : title={page.title()!r}")
            dump_links(page, "https://fr.vicon.eu", "Vicon produits")
        except Exception as e:
            log.warning(f"Vicon catégorie : échec ({e})")
        page.close()

        # Maschio Gaspardo retry avec UA réaliste
        page = browser.new_page(user_agent=UA)
        try:
            page.goto("https://www.maschiogaspardo.com/fr_fr/", timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            log.info(f"\n=== Maschio Gaspardo retry UA : title={page.title()!r} url={page.url}")
            dump_links(page, page.url, "Maschio Gaspardo retry")
        except Exception as e:
            log.warning(f"Maschio Gaspardo retry : échec ({e})")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
